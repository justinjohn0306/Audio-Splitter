import os
import sys
import tempfile
import zipfile
from pydub import AudioSegment, silence
from PyQt5 import QtCore
from PyQt5.QtGui import QPalette, QFont, QIntValidator, QLinearGradient, QBrush, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget,
    QProgressBar, QListWidget, QListWidgetItem, QLineEdit,
    QFileDialog, QApplication, QSlider, QMessageBox, QComboBox,
    QHBoxLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from multiprocessing import freeze_support


def remove_silence(audio, silence_thresh=-40):
    silence_thresh = float(silence_thresh)  # Convert silence_thresh to float
    non_silent_audio = silence.split_on_silence(audio, min_silence_len=1000, silence_thresh=silence_thresh)
    return non_silent_audio


def join_audio_segments(segments, segment_duration, min_segment_duration):
    joined_segments = []
    current_segment = None
    for segment in segments:
        if current_segment is None:
            current_segment = segment
        elif len(current_segment) < segment_duration * 1000:
            current_segment += segment
        else:
            # Check if the current segment is longer than the minimum duration
            if len(current_segment) >= min_segment_duration * 1000:
                joined_segments.append(current_segment)
            current_segment = segment

    if current_segment is not None:
        # Check if the current segment is longer than the minimum duration
        if len(current_segment) >= min_segment_duration * 1000:
            joined_segments.append(current_segment)

    return joined_segments


def process_audio_file(audio_file_path, segment_duration, min_segment_duration=3, silence_thresh=-40, output_format="wav"):
    audio = AudioSegment.from_file(audio_file_path)

    if isinstance(silence_thresh, str):
        output_format = silence_thresh
        silence_thresh = -40

    silence_thresh = float(silence_thresh)

    non_silent_audio = remove_silence(audio, silence_thresh=silence_thresh)

    segments = []
    for j, segment in enumerate(non_silent_audio):
        if len(segment) >= segment_duration * 1000:
            segment = segment[:segment_duration * 1000]  # Trim segment to the specified duration
            segments.extend(segment[0:segment_duration * 1000] for segment in segment[::segment_duration * 1000])
        else:
            segments.append(segment)

    joined_segments = join_audio_segments(segments, segment_duration, min_segment_duration)

    final_segments = []
    for segment in joined_segments:
        if len(segment) >= min_segment_duration * 1000:
            final_segments.append(segment)

    temp_files = []
    for k, segment in enumerate(final_segments):
        segment_file_name = f"segment_{k + 1}.{output_format}"
        temp_file = tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False)
        segment.export(temp_file.name, format=output_format)  # Write segment to the temp file
        temp_file.close()  # Close the temp file
        temp_file_name = os.path.join(os.path.dirname(temp_file.name), segment_file_name)

        # Check if the destination file already exists
        counter = 1
        while os.path.exists(temp_file_name):
            segment_file_name = f"segment_{k + 1}_{counter}.{output_format}"
            temp_file_name = os.path.join(os.path.dirname(temp_file.name), segment_file_name)
            counter += 1

        os.rename(temp_file.name, temp_file_name)  # Rename the temp file
        temp_files.append((segment_file_name, temp_file_name))

    return temp_files


class WorkerThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal()

    def __init__(self, audio_files, segment_duration, min_segment_duration, silence_thresh, output_format, output_dir):
        super().__init__()
        self.audio_files = audio_files
        self.segment_duration = segment_duration
        self.min_segment_duration = min_segment_duration
        self.silence_thresh = silence_thresh
        self.output_format = output_format
        self.output_dir = output_dir

    def run(self):
        processed_files = []
        total_files = len(self.audio_files)
        completed_files = 0

        for audio_file in self.audio_files:
            temp_files = process_audio_file(audio_file, self.segment_duration, self.min_segment_duration, self.silence_thresh, self.output_format)
            processed_files.extend(temp_files)
            completed_files += 1
            self.progress_signal.emit(int(completed_files / total_files * 100))

        output_zip_file = os.path.join(self.output_dir, "split_audio.zip")

        with zipfile.ZipFile(output_zip_file, 'w') as output_zip:
            for segment_file_name, temp_file in processed_files:
                output_zip.write(temp_file, arcname=segment_file_name)
                os.remove(temp_file)  # Clean up temp files

        self.finished_signal.emit()


class AudioSplitterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Audio Splitter")
        self.setGeometry(100, 100, 500, 400)
        font = QFont("Arial", 12)
        self.setFont(font)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Add Audio Files
        add_audio_files_button = QPushButton("Add Audio Files")
        add_audio_files_button.clicked.connect(self.add_audio_files)
        main_layout.addWidget(QLabel("Audio Files:"))

        # Create QListWidget for audio files
        self.audio_files_list = QListWidget()
        self.audio_files_list.setAcceptDrops(True)  # Enable drag and drop
        self.audio_files_list.viewport().setAcceptDrops(True)  # Enable drag and drop
        self.audio_files_list.setDragDropMode(QListWidget.InternalMove)  # Allow rearranging items
        self.audio_files_list.dragEnterEvent = self.drag_enter_event  # Override dragEnterEvent
        self.audio_files_list.dragMoveEvent = self.drag_move_event  # Override dragMoveEvent
        self.audio_files_list.dropEvent = self.drop_event  # Override dropEvent

        main_layout.addWidget(self.audio_files_list)
        main_layout.addWidget(add_audio_files_button)

        # Remove Selected Files
        remove_selected_button = QPushButton("Remove Selected Files")
        remove_selected_button.clicked.connect(self.remove_selected_files)
        main_layout.addWidget(remove_selected_button)

        # Clear All Files
        clear_all_button = QPushButton("Clear All Files")
        clear_all_button.clicked.connect(self.clear_all_files)
        main_layout.addWidget(clear_all_button)

        # Create input for segment duration
        self.segment_duration_input = QLineEdit()
        self.segment_duration_input.setValidator(QIntValidator(1, 999999))
        self.segment_duration_input.setText("10")
        main_layout.addWidget(QLabel("Segment Duration (seconds):"))
        main_layout.addWidget(self.segment_duration_input)

        # Create ComboBox for output format
        self.output_format_input = QComboBox()
        self.output_format_input.addItems(["wav", "mp3", "flac", "ogg"])
        main_layout.addWidget(QLabel("Output Format:"))
        main_layout.addWidget(self.output_format_input)

        # Create slider for silence threshold
        main_layout.addWidget(QLabel("Silence Threshold (dB):"))
        threshold_layout = QHBoxLayout()

        self.silence_thresh_input = QSlider(Qt.Horizontal)
        self.silence_thresh_input.setRange(-100, 0)
        self.silence_thresh_input.setValue(-40)
        self.silence_thresh_input.valueChanged.connect(self.update_threshold_label)

        threshold_layout.addWidget(self.silence_thresh_input)

        # Create QLabel for displaying the current value of the QSlider
        self.threshold_value_label = QLabel()
        self.update_threshold_label()  # Display initial value
        threshold_layout.addWidget(self.threshold_value_label)

        main_layout.addLayout(threshold_layout)

        # Create start button
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start)
        main_layout.addWidget(self.start_button)

        # Create progress bar
        self.progress_bar = QProgressBar()
        main_layout.addWidget(self.progress_bar)

        self.setLayout(main_layout)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Apply gradient background
        self.set_gradient_background()

        self.setStyleSheet('''
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                color: #404040;
            }
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                padding: 6px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #005999;
            }
            QPushButton:pressed {
                background-color: #004070;
            }
            QSlider {
                background-color: #bfbfbf;
            }
            QSlider::handle {
                background-color: #8cbf26;
                border: 1px solid #5c912b;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                selection-background-color: #0078d7;
                selection-color: white;
            }
        ''')

    def set_gradient_background(self):
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#f0f0f0"))
        gradient.setColorAt(1, QColor("#a3a3a3"))

        palette = QPalette()
        palette.setBrush(QPalette.Window, QBrush(gradient))

        self.setPalette(palette)

    def update_threshold_label(self):
        self.threshold_value_label.setText(str(self.silence_thresh_input.value()))

    def add_audio_files(self):
        audio_files, _ = QFileDialog.getOpenFileNames(self, "Select Audio Files")
        self.add_audio_files_to_list(audio_files)

    def add_audio_files_to_list(self, audio_files):
        for audio_file in audio_files:
            item = QListWidgetItem(audio_file)
            self.audio_files_list.addItem(item)

    def remove_selected_files(self):
        for item in self.audio_files_list.selectedItems():
            self.audio_files_list.takeItem(self.audio_files_list.row(item))

    def clear_all_files(self):
        self.audio_files_list.clear()

    def drag_enter_event(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def drag_move_event(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def drop_event(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            audio_files = [url.toLocalFile() for url in urls if url.isLocalFile()]
            self.add_audio_files_to_list(audio_files)
            event.accept()
        else:
            event.ignore()

    def start(self):
        if self.audio_files_list.count() == 0:
            QMessageBox.warning(self, "No Audio Files", "Please select at least one audio file.")
            return

        segment_duration = self.segment_duration_input.text()
        if not segment_duration:
            QMessageBox.warning(self, "Segment Duration Missing", "Please enter a segment duration.")
            return

        min_segment_duration = 3  # Define the minimum segment duration here
        audio_files = [self.audio_files_list.item(i).text() for i in range(self.audio_files_list.count())]
        segment_duration = int(segment_duration)
        silence_thresh = self.silence_thresh_input.value()
        output_format = self.output_format_input.currentText()
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")

        self.worker_thread = WorkerThread(audio_files, segment_duration, min_segment_duration, silence_thresh, output_format, output_dir)
        self.worker_thread.progress_signal.connect(self.progress_bar.setValue)
        self.worker_thread.finished_signal.connect(self.finished)

        self.start_button.setEnabled(False)
        self.worker_thread.start()

    def finished(self):
        self.start_button.setEnabled(True)
        QMessageBox.information(self, "Finished", "Audio files have been split and saved.")


def main():
    QtCore.QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    splitter_window = AudioSplitterWindow()
    splitter_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    freeze_support()
    main()
