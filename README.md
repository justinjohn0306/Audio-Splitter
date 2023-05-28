# Audio Splitter

Audio Splitter is a Python application that allows you to split audio files into segments based on silence detection.

## Installation

You can download the latest version of the installer for Windows from the [Releases](https://github.com/justinjohn0306/Audio-Splitter/releases) tab. Choose the appropriate installer file based on your system architecture (32-bit or 64-bit).

Once the installer file is downloaded, simply double-click on it to start the installation process. Follow the on-screen instructions to complete the installation.

## Usage

1. Launch the Audio Splitter application.
2. Click on the "Add Audio Files" button to select the audio files you want to split. You can also drag and drop audio files into the application.
3. Specify the segment duration in seconds using the "Segment Duration" input field.
4. Choose the desired output format from the "Output Format" dropdown list.
5. Adjust the silence threshold using the "Silence Threshold" slider. This determines the sensitivity of the silence detection algorithm. Lower values make the algorithm more sensitive to silence, while higher values make it less sensitive.
6. Click on the "Start" button to begin the splitting process.
7. The progress bar will show the progress of the splitting operation.
8. Once the splitting is complete, a message box will appear indicating the successful split.
9. The resulting audio segments will be saved in a ZIP file named "split_audio.zip" in the specified output directory.

**Note:** The silence threshold represents the decibel level below which audio is considered silent. Setting a lower value will split the audio more frequently, even for lower levels of silence. Setting a higher value will split the audio less frequently, requiring longer periods of silence for a split to occur.

## Features

- Split audio files into segments based on silence detection.
- Specify the segment duration and minimum segment duration.
- Adjust the silence threshold for accurate silence detection.
- Support for various output formats such as WAV, MP3, FLAC, and OGG.
- Drag and drop support for adding audio files.
- Progress bar to track the splitting progress.



## Acknowledgements

I would like to thank the following individuals/projects for their contributions and inspiration:

- [PyDub](https://github.com/jiaaro/pydub): A simple and easy-to-use audio processing library for Python.
- [PyQt5](https://riverbankcomputing.com/software/pyqt/): A comprehensive set of Python bindings for Qt application framework.
