import sys, os, json
import cv2
import numpy as np

# ── OpenCV Unicode 路径支持 ──
def _imread(path, flags=cv2.IMREAD_COLOR):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)
def _imwrite(path, img, params=None):
    cv2.imencode(os.path.splitext(path)[1] or '.png', img, params or [])[1].tofile(path)

# ──────────────────────────────────────────────
#  工具函数
# ──────────────────────────────────────────────

def _clamp_dict(d, img_w=99999, img_h=99999):
    return {
        'x': max(0, min(d['x'], img_w - 1)),
        'y': max(0, min(d['y'], img_h - 1)),
        'w': max(1, min(d['w'], img_w - d['x'])),
        'h': max(1, min(d['h'], img_h - d['y'])),
    }

def _draw_box(img, box_dict, color, label, pos='top-left'):
    r = _clamp_dict(box_dict)
    cv2.rectangle(img, (r['x'], r['y']), (r['x'] + r['w'], r['y'] + r['h']), color, 3)
    if pos == 'top-left':
        tx, ty = r['x'] + 3, r['y'] + 22
    elif pos == 'bottom-left':
        tx, ty = r['x'] + 3, r['y'] + r['h'] - 8
    else:
        tx, ty = r['x'] + 3, r['y'] - 8
    cv2.putText(img, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def _letterbox(img, target_size=640):
    h, w = img.shape[:2]
    scale = min(target_size / w, target_size / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
    dw = (target_size - new_w) // 2
    dh = (target_size - new_h) // 2
    canvas[dh:dh+new_h, dw:dw+new_w] = resized
    return canvas, scale, dw, dh

def _nms(boxes_xyxy, scores, iou_threshold=0.45):
    if len(boxes_xyxy) == 0:
        return np.array([], dtype=int)
    x1, y1, x2, y2 = boxes_xyxy[:, 0], boxes_xyxy[:, 1], boxes_xyxy[:, 2], boxes_xyxy[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(i)
        if len(order) == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0, xx2 - xx1)
        h = np.maximum(0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-10)
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    return np.array(keep)


# ──────────────────────────────────────────────
#  YOLO 盲盒检测器（直接 ONNX Runtime）
# ──────────────────────────────────────────────

class BlindBoxDetector:
    CALIBRATION = {
        'box':    (30, 5, 250, 495),
        'layer2': (59, 249, 84, 94),
        'layer3': (55, 388, 85, 100),
    }
    L2_REL = {
        'x': (59 - 30) / 250,
        'y': (249 - 5) / 495,
        'w': 84 / 250,
        'h': 94 / 495,
    }
    L3_REL = {
        'x': (55 - 30) / 250,
        'y': (388 - 5) / 495,
        'w': 85 / 250,
        'h': 100 / 495,
    }

    def __init__(self, model_path=None, conf_threshold=0.25):
        self.conf_threshold = conf_threshold
        self.ort_session = None
        self.model_path = None
        self.nc = 3

        if model_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            model_path = os.path.join(base, "blind_box_v5.onnx")

        if not os.path.exists(model_path):
            print(f"[BlindBoxDetector] 模型文件不存在: {model_path}")
            return

        try:
            import onnxruntime as ort
            self.ort_session = ort.InferenceSession(
                model_path,
                providers=['CPUExecutionProvider']
            )
            self.model_path = model_path

            inp = self.ort_session.get_inputs()[0]
            self.ort_input_name = inp.name
            out = self.ort_session.get_outputs()[0]
            self.ort_output_name = out.name
            out_shape = out.shape

            self.nc = (out_shape[1] - 4) if len(out_shape) > 1 else 3
            self.imgsz = inp.shape[2] if len(inp.shape) > 2 else 640

            size_mb = os.path.getsize(model_path) / 1024 / 1024
            print(f"[BlindBoxDetector] ONNX加载成功: {os.path.basename(model_path)} ({size_mb:.1f}MB), 类别数={self.nc}, 推理尺寸={self.imgsz}")
        except Exception as e:
            print(f"[BlindBoxDetector] ONNX Runtime加载失败: {e}")
            self._load_ultralytics_fallback(model_path)

    def _load_ultralytics_fallback(self, model_path):
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.nc = getattr(self.model.model, 'nc', 3) if hasattr(self.model, 'model') else 3
            size_mb = os.path.getsize(model_path) / 1024 / 1024
            print(f"[BlindBoxDetector] 降级到 ultralytics: {os.path.basename(model_path)} ({size_mb:.1f}MB)")
        except Exception as e:
            print(f"[BlindBoxDetector] ultralytics 降级失败: {e}")
            self.model = None

    def update_conf_threshold(self, threshold):
        old = self.conf_threshold
        self.conf_threshold = max(0.01, min(0.99, threshold))

    @property
    def is_ready(self):
        return self.ort_session is not None or (hasattr(self, 'model') and self.model is not None)

    def get_status(self):
        """获取模型加载状态（用于调试输出）"""
        if self.ort_session is not None:
            return "✅ 盲盒检测模型已加载 (ONNX Runtime)"
        elif hasattr(self, 'model') and self.model is not None:
            return "⚠️ 盲盒检测模型已加载 (Ultralytics 降级模式，部分环境可能不稳定)"
        else:
            reason = ""
            if self.model_path and not os.path.exists(self.model_path):
                reason = " - 模型文件不存在"
            else:
                reason = " - ONNX Runtime 加载失败，Ultralytics 降级也失败"
            return f"❌ 盲盒检测模型未加载{reason}"

    def detect(self, target_image):
        if target_image is None:
            return {'detected': False, 'score': 0, 'method': 'yolo_unavailable'}

        if self.ort_session is not None:
            return self._detect_ort(target_image)
        elif hasattr(self, 'model') and self.model is not None:
            return self._detect_ultralytics(target_image)
        else:
            return {'detected': False, 'score': 0, 'method': 'yolo_unavailable'}

    def _detect_ort(self, target_image):
        h, w = target_image.shape[:2]
        rgb = cv2.cvtColor(target_image, cv2.COLOR_BGR2RGB)
        canvas, scale, dw, dh = _letterbox(rgb, self.imgsz)
        blob = canvas.transpose(2, 0, 1).astype(np.float32)[None, ...] / 255.0

        outputs = self.ort_session.run(
            [self.ort_output_name],
            {self.ort_input_name: blob}
        )
        pred = outputs[0][0]
        pred = pred.transpose(1, 0)

        cx = pred[:, 0]
        cy = pred[:, 1]
        bw = pred[:, 2]
        bh = pred[:, 3]
        cls_scores = pred[:, 4:]

        max_scores = cls_scores.max(axis=1)
        max_classes = cls_scores.argmax(axis=1)
        mask = max_scores > self.conf_threshold
        if not mask.any():
            return {'detected': False, 'score': 0, 'method': 'yolo_none'}

        cx, cy, bw, bh = cx[mask], cy[mask], bw[mask], bh[mask]
        scores = max_scores[mask]
        classes = max_classes[mask]

        x1 = (cx - bw / 2 - dw) / scale
        y1 = (cy - bh / 2 - dh) / scale
        x2 = (cx + bw / 2 - dw) / scale
        y2 = (cy + bh / 2 - dh) / scale

        x1 = np.clip(x1, 0, w)
        y1 = np.clip(y1, 0, h)
        x2 = np.clip(x2, 0, w)
        y2 = np.clip(y2, 0, h)

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

        blind_mask = classes == 0
        l2_mask = classes == 1
        l3_mask = classes == 2

        blind_boxes = []
        l2_boxes = []
        l3_boxes = []

        if blind_mask.any():
            idx = _nms(boxes_xyxy[blind_mask], scores[blind_mask])
            for i in idx:
                bx1, by1, bx2, by2 = boxes_xyxy[blind_mask][i]
                blind_boxes.append(({'x': int(bx1), 'y': int(by1), 'w': int(bx2-bx1), 'h': int(by2-by1)}, float(scores[blind_mask][i])))

        if l2_mask.any():
            idx = _nms(boxes_xyxy[l2_mask], scores[l2_mask])
            for i in idx:
                bx1, by1, bx2, by2 = boxes_xyxy[l2_mask][i]
                l2_boxes.append(({'x': int(bx1), 'y': int(by1), 'w': int(bx2-bx1), 'h': int(by2-by1)}, float(scores[l2_mask][i])))

        if l3_mask.any():
            idx = _nms(boxes_xyxy[l3_mask], scores[l3_mask])
            for i in idx:
                bx1, by1, bx2, by2 = boxes_xyxy[l3_mask][i]
                l3_boxes.append(({'x': int(bx1), 'y': int(by1), 'w': int(bx2-bx1), 'h': int(by2-by1)}, float(scores[l3_mask][i])))

        if not blind_boxes:
            return {'detected': False, 'score': 0, 'method': 'yolo_none'}

        best_box, best_conf = max(blind_boxes, key=lambda x: x[1])
        best_l2 = max(l2_boxes, key=lambda x: x[1])[0] if l2_boxes else None
        best_l3 = max(l3_boxes, key=lambda x: x[1])[0] if l3_boxes else None

        if best_l2 is None:
            best_l2 = self._roi_from_box(best_box, self.L2_REL, w, h)
        if best_l3 is None:
            best_l3 = self._roi_from_box(best_box, self.L3_REL, w, h)

        return {
            'detected': True,
            'score': min(100, best_conf * 100),
            'method': f"yolo_ort:{best_conf:.3f}",
            'box': best_box,
            'layer2': best_l2,
            'layer3': best_l3,
        }

    def _detect_ultralytics(self, target_image):
        h, w = target_image.shape[:2]
        results = self.model(target_image, imgsz=640, conf=self.conf_threshold, verbose=False)
        boxes = results[0].boxes
        if len(boxes) == 0:
            return {'detected': False, 'score': 0, 'method': 'yolo_none'}

        blind_boxes = []
        layer2_boxes = []
        layer3_boxes = []
        for b in boxes:
            cls_id = int(b.cls.item())
            x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
            conf = float(b.conf.item())
            box = {'x': x1, 'y': y1, 'w': x2-x1, 'h': y2-y1}
            if cls_id == 0:
                blind_boxes.append((box, conf))
            elif cls_id == 1:
                layer2_boxes.append((box, conf))
            elif cls_id == 2:
                layer3_boxes.append((box, conf))

        if not blind_boxes:
            return {'detected': False, 'score': 0, 'method': 'yolo_none'}

        best_box, best_conf = max(blind_boxes, key=lambda x: x[1])
        best_l2 = max(layer2_boxes, key=lambda x: x[1])[0] if layer2_boxes else None
        best_l3 = max(layer3_boxes, key=lambda x: x[1])[0] if layer3_boxes else None

        if best_l2 is None:
            best_l2 = self._roi_from_box(best_box, self.L2_REL, w, h)
        if best_l3 is None:
            best_l3 = self._roi_from_box(best_box, self.L3_REL, w, h)

        return {
            'detected': True,
            'score': min(100, best_conf * 100),
            'method': f"yolo_ultra:{best_conf:.3f}",
            'box': best_box,
            'layer2': best_l2,
            'layer3': best_l3,
        }

    def _roi_from_box(self, box, rel, img_w, img_h):
        x = int(box['x'] + box['w'] * rel['x'])
        y = int(box['y'] + box['h'] * rel['y'])
        rw = int(box['w'] * rel['w'])
        rh = int(box['h'] * rel['h'])
        return _clamp_dict({'x': x, 'y': y, 'w': rw, 'h': rh}, img_w, img_h)

    def draw_result(self, target_image, result, output_path=None):
        draw = target_image.copy()
        if result.get('detected') and 'box' in result:
            _draw_box(draw, result['box'], (0, 255, 0),
                      f"YOLO [{result.get('score', 0):.0f}]")
        if 'layer2' in result:
            _draw_box(draw, result['layer2'], (0, 0, 255), "L2", pos='bottom-left')
        if 'layer3' in result:
            _draw_box(draw, result['layer3'], (255, 0, 0), "L3", pos='bottom-left')
        if output_path:
            _imwrite(output_path, draw)
        return draw

    def vote_sequence(self, frames, min_votes=2, min_avg=0.72):
        if not frames or len(frames) < min_votes:
            return None
        matched = [r for r in [self.detect(f) for f in frames] if r.get('detected')]
        if len(matched) < min_votes:
            return None
        avg_score = sum(r['score'] for r in matched) / len(matched)
        if avg_score < min_avg * 100:
            return None
        best = max(matched, key=lambda r: r['score'])
        best['vote_count'] = len(matched)
        best['total_frames'] = len(frames)
        best['vote_score'] = avg_score
        return best


class BloodlineDetector:
    """血脉+加成检测器 (ONNX Runtime)
    使用 YOLO26n 模型识别盲盒中的血脉类型和加成类型
    复用 BlindBoxDetector 的技术方案，确保跨平台一致性
    """
    BLOODLINE_NAMES = ['普通', '奇异', '异色', '混血', '污染']
    BONUS_NAMES = ['生命', '速度', '物攻', '魔攻', '物防', '魔防']
    ALL_NAMES = BLOODLINE_NAMES + BONUS_NAMES

    def __init__(self, model_path=None, conf_threshold=0.15):
        self.conf_threshold = conf_threshold
        self.ort_session = None
        self.model_path = None
        self.imgsz = 640
        self._load_error = None

        if model_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            model_path = os.path.join(base, "runs", "mx_yolo26n", "weights", "best.onnx")

        if not os.path.exists(model_path):
            self._load_error = "模型文件不存在"
            print(f"[BloodlineDetector] 模型文件不存在: {model_path}")
            return

        try:
            import onnxruntime as ort
            self.ort_session = ort.InferenceSession(
                model_path,
                providers=['CPUExecutionProvider']
            )
            self.model_path = model_path

            inp = self.ort_session.get_inputs()[0]
            self.ort_input_name = inp.name
            out = self.ort_session.get_outputs()[0]
            self.ort_output_name = out.name

            self.imgsz = inp.shape[2] if len(inp.shape) > 2 else 640

            size_mb = os.path.getsize(model_path) / 1024 / 1024
            print(f"[BloodlineDetector] ONNX加载成功: {os.path.basename(model_path)} ({size_mb:.1f}MB), 推理尺寸={self.imgsz}")
        except ImportError:
            self._load_error = "ONNX Runtime 未安装 (缺少 onnxruntime 库)"
            print(f"[BloodlineDetector] ONNX Runtime 未安装")
        except Exception as e:
            self._load_error = f"加载异常: {e}"
            print(f"[BloodlineDetector] ONNX Runtime加载失败: {e}")

    @property
    def is_ready(self):
        return self.ort_session is not None

    def get_status(self):
        """获取模型加载状态（用于调试输出）"""
        if self.ort_session is not None:
            return "✅ 血脉加成检测模型已加载 (ONNX Runtime)"
        elif self._load_error:
            return f"❌ 血脉加成检测模型未加载 - {self._load_error}"
        return "❌ 血脉加成检测模型未加载"

    def detect(self, target_image):
        if target_image is None or self.ort_session is None:
            return []

        h, w = target_image.shape[:2]
        rgb = cv2.cvtColor(target_image, cv2.COLOR_BGR2RGB)
        canvas, scale, dw, dh = _letterbox(rgb, self.imgsz)
        blob = canvas.transpose(2, 0, 1).astype(np.float32)[None, ...] / 255.0

        outputs = self.ort_session.run(
            [self.ort_output_name],
            {self.ort_input_name: blob}
        )

        pred = outputs[0][0]

        x1 = pred[:, 0]
        y1 = pred[:, 1]
        x2 = pred[:, 2]
        y2 = pred[:, 3]
        conf = pred[:, 4]
        cls_ids = pred[:, 5].astype(int)

        mask = conf > self.conf_threshold
        if not mask.any():
            return []

        x1, y1, x2, y2 = x1[mask], y1[mask], x2[mask], y2[mask]
        conf = conf[mask]
        cls_ids = cls_ids[mask]

        x1 = (x1 - dw) / scale
        y1 = (y1 - dh) / scale
        x2 = (x2 - dw) / scale
        y2 = (y2 - dh) / scale

        x1 = np.clip(x1, 0, w)
        y1 = np.clip(y1, 0, h)
        x2 = np.clip(x2, 0, w)
        y2 = np.clip(y2, 0, h)

        boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)

        keep = _nms(boxes_xyxy, conf)

        detections = []
        for i in keep:
            detections.append({
                'cls_id': int(cls_ids[i]),
                'conf': float(conf[i]),
                'xyxy': boxes_xyxy[i].tolist(),
            })

        return detections