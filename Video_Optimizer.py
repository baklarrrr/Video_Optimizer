import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog
from moviepy.editor import VideoFileClip
import subprocess
import time

# GUI theme and icon
import customtkinter
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

stream_infos = []

# Functions
def discover_videos(path):
    video_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mov')):
                video_files.append(os.path.join(root, file))
    return video_files

def determine_resolution(video_file):
    video = VideoFileClip(video_file)
    return video.size

def determine_duration(video_file):
    video = VideoFileClip(video_file)
    return video.duration

def assign_encoding_settings(resolution):
    if gpu_var.get() == "NVIDIA":
        # Adjust the settings for NVENC
        if resolution[1] >= 7680:  # 8K
            return "-rc vbr -cq 18 -preset slow"
        elif resolution[1] >= 3840:  # 4K
            return "-rc vbr -cq 19 -preset slow"
        elif resolution[1] >= 2560:  # QHD
            return "-rc vbr -cq 20 -preset slow"
        elif resolution[1] >= 1080:  # HD 1080p
            return "-rc vbr -cq 21 -preset slow"
        else:  # Lower resolutions
            return "-rc vbr -cq 23 -preset slow"
    else:
        # Original settings for non-NVENC
        if resolution[1] >= 7680:  # 8K
            return "-crf 20 -preset fast"
        elif resolution[1] >= 3840:  # 4K
            return "-crf 22 -preset fast"
        elif resolution[1] >= 2560:  # QHD
            return "-crf 23 -preset fast"
        elif resolution[1] >= 1080:  # HD 1080p
            return "-crf 23 -preset fast"
        else:  # Lower resolutions
            return "-crf 28 -preset fast"


def re_encode_video(video_file, encoding_settings):
    output_file = os.path.join(output_directory, f"{os.path.splitext(os.path.basename(video_file))[0]}_optimized.mp4")

    selected_codec = codec_var.get()
    video_codec_string = f"-c:v {selected_codec}"  # default codec selection
    if gpu_var.get() == "NVIDIA":
        if selected_codec == "libx265":
            video_codec_string = "-c:v hevc_nvenc"  # NVIDIA GPU acceleration for H.265
        elif selected_codec == "libx264":
            video_codec_string = "-c:v h264_nvenc"  # NVIDIA GPU acceleration for H.264
        elif selected_codec == "libvpx-vp9":
            print("NVIDIA GPU acceleration doesn't support VP9. Reverting to CPU encoding for VP9.")

    command = f'C:\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe -i "{video_file}" {video_codec_string} {encoding_settings} -c:a aac -b:a 128k -f mp4 "{output_file}"'
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    stream_info = {
        'filename': video_file,
        'input_codec': None,
        'output_codec': None
    }

    for line in process.stderr:
        if "Stream mapping:" in line:
            stream_mapping = line.strip().split("Stream mapping:")[1].strip()
            if "->" in stream_mapping:
                input_codec = stream_mapping.split("->")[0].split()[-1][1:-1]
                output_codec = stream_mapping.split("->")[1].split()[-1][1:-1]
                stream_info['input_codec'] = input_codec
                stream_info['output_codec'] = output_codec
        print(line.strip())  # Keep the FFmpeg output to the console

    stream_infos.append(stream_info)
    return stream_info

def process_video(video_file):
    resolution = determine_resolution(video_file)
    encoding_settings = assign_encoding_settings(resolution)
    stream_info = re_encode_video(video_file, encoding_settings)
    stream_infos.append((video_file, stream_info))
    print(f"Captured stream info for {video_file}: {stream_info}")

def determine_total_frames(video_file):
    cmd = f'C:\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe -i "{video_file}" -map 0:v:0 -c copy -f nut -y NUL'
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    stdout, stderr = process.communicate()
    frames = [x for x in stderr.split("\n") if "frame=" in x]
    if frames:
        return int(frames[-1].split("frame=")[1].split("fps")[0])
    return None

def update_progress_bar(percentage):
    progress_bar['value'] = percentage
    root.update_idletasks()

def get_stream_info(video_file):
    # Fetch codec information
    codec_info_cmd = f'C:\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe -i "{video_file}"'
    process = subprocess.Popen(codec_info_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    _, stderr = process.communicate()
    
    stream_info = ""
    for line in stderr.split("\n"):
        if "Stream mapping:" in line:
            stream_info = line.strip()
            next_line_index = stderr.split("\n").index(line) + 1
            if next_line_index < len(stderr.split("\n")):
                stream_info += " (" + stderr.split("\n")[next_line_index].strip() + ")"
    return stream_info

def display_stream_infos():
    info_dialog = tk.Toplevel(root)
    info_dialog.title("Stream Mapping Info")
    info_dialog.geometry("600x400")

    text_area = tk.Text(info_dialog, wrap=tk.WORD)
    text_area.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

    for info in stream_infos:
        text_area.insert(tk.END, f"Video: {os.path.basename(info['filename'])}\n")
        text_area.insert(tk.END, f"Stream mapping: {info['input_codec']} -> {info['output_codec']}\n\n")
    text_area.configure(state=tk.DISABLED)  # Make the text read-only

    close_button = tk.Button(info_dialog, text="Close", command=info_dialog.destroy)
    close_button.pack(pady=10)

def start_processing_videos():
    global input_directory, output_directory
    input_directory = filedialog.askdirectory(title="Select Input Directory")
    if not input_directory:
        return
    output_directory = filedialog.askdirectory(title="Select Output Directory")
    if not output_directory:
        return

    video_files = discover_videos(input_directory)
    # Display stream info
    display_stream_infos()

    # Then proceed with encoding each video
    for video_file in video_files:
        threading.Thread(target=re_encode_video, args=(video_file, assign_encoding_settings(determine_resolution(video_file)))).start()

class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.text = text
        self.widget.bind("<Enter>", self.showtip)
        self.widget.bind("<Leave>", self.hidetip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def create_tooltip(widget, text):
    ToolTip(widget, text)

# GUI
root = tk.Tk()
root.geometry("500x350")
root.title("Video Optimizer")
root.iconbitmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'optimizer.ico'))

frame = tk.Frame(master=root)
frame.pack(pady=20, padx=60, fill="both", expand=True)

label = tk.Label(master=frame, text="Video Optimizer")
label.pack(pady=12, padx=10)

codec_var = tk.StringVar()
codec_var.set("libx265")  # Default codec

h265_radio = tk.Radiobutton(frame, text="H.265 (HEVC)", variable=codec_var, value="libx265")
h264_radio = tk.Radiobutton(frame, text="H.264 (AVC)", variable=codec_var, value="libx264")
vp9_radio = tk.Radiobutton(frame, text="VP9", variable=codec_var, value="libvpx-vp9")

h265_radio.pack(anchor=tk.W, pady=5)
h264_radio.pack(anchor=tk.W, pady=5)
vp9_radio.pack(anchor=tk.W, pady=5)

start_button = tk.Button(master=frame, text="Select Folders and Start", command=start_processing_videos)
start_button.pack(pady=12, padx=10)

progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=12, padx=10, fill="both", expand=True)


h265_radio_tooltip = "H.265 (HEVC) - Efficient but might not be supported by all browsers."
h264_radio_tooltip = "H.264 (AVC) - Supported by almost all browsers and devices."
vp9_radio_tooltip = "VP9 - Supported by modern browsers, more efficient than H.264 but less widely supported."

info_button = tk.Button(master=frame, text="Show Stream Mapping Info", command=display_stream_infos)
info_button.pack(pady=10, padx=10)

# GPU Acceleration
gpu_var = tk.StringVar()
gpu_var.set("None")  # Default choice

gpu_label = tk.Label(master=frame, text="Choose GPU Acceleration:")
gpu_label.pack(pady=5, padx=10, anchor=tk.W)

gpu_options = ["None", "NVIDIA", "AMD", "Intel"]
gpu_dropdown = ttk.Combobox(frame, textvariable=gpu_var, values=gpu_options)
gpu_dropdown.pack(pady=5, padx=10, anchor=tk.W)

create_tooltip(h265_radio, h265_radio_tooltip)
create_tooltip(h264_radio, h264_radio_tooltip)
create_tooltip(vp9_radio, vp9_radio_tooltip)


root.mainloop()
