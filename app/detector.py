import cv2
import numpy as np
import os
import time
from threading import Thread, Event
from google.generativeai import GenerativeModel
from .alert import trigger_alert
from .brands import get_stream_capture

class CameraProcessor:
    def __init__(self, url: str, brand: str, threshold: int, email_addresses: list):
        self.url = url
        self.brand = brand
        self.threshold = threshold
        self.email_addresses = email_addresses
        self.stop_event = Event()
        self.thread = Thread(target=self._process, daemon=True)
        self.model = GenerativeModel('gemini-pro')  # uses GEMINI_API_KEY env var

    def run(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)

    def _process(self):
        cap = get_stream_capture(self.url, self.brand)
        if cap is None:
            print(f"Failed to obtain stream for {self.url} (brand={self.brand})")
            return
        if not cap.isOpened():
            print(f"Failed to open stream {self.url}")
            return
        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            # Resize for faster inference
            small = cv2.resize(frame, (640, 360))
            _, buf = cv2.imencode('.jpg', small)
            image_bytes = buf.tobytes()
            try:
                response = self.model.generate_content([
                    "Count the number of distinct people in this image. Respond with only an integer.",
                    image_bytes
                ])
                count_text = response.text.strip()
                count = int(''.join(filter(str.isdigit, count_text)))
            except Exception as e:
                print(f"Model inference error: {e}")
                continue
            if count >= self.threshold:
                trigger_alert(count, self.email_addresses)
            # Sleep briefly to avoid hammering the model
            time.sleep(2)
        cap.release()

    def run(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)

    def _process(self):
        cap = cv2.VideoCapture(self.url)
        if not cap.isOpened():
            print(f"Failed to open stream {self.url}")
            return
        while not self.stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            # Resize for faster inference
            small = cv2.resize(frame, (640, 360))
            _, buf = cv2.imencode('.jpg', small)
            image_bytes = buf.tobytes()
            try:
                response = self.model.generate_content([
                    "Count the number of distinct people in this image. Respond with only an integer.",
                    image_bytes
                ])
                count_text = response.text.strip()
                count = int(''.join(filter(str.isdigit, count_text)))
            except Exception as e:
                print(f"Model inference error: {e}")
                continue
            if count >= self.threshold:
                trigger_alert(count, self.phone_numbers)
            # Sleep briefly to avoid hammering the model
            time.sleep(2)
        cap.release()
