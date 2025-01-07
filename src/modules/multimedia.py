import click
import subprocess
import os
import sys
import mimetypes
from utils.helper import check_path_type,resolve_path, run_command, parse_size_to_string

@click.group()
def module():
    """
    Multimedia analysis module.
    """
    pass

@module.command()
@click.argument('file_path', type=click.Path())
@click.argument('output_path', type=click.Path())
@click.option('--resize', type=(int, int), help="Resize the image to WIDTH HEIGHT. Example: --resize 1920 1080")
@click.option('--crop', type=(int, int, int, int), help="Crop the image. Provide WIDTH HEIGHT X_OFFSET Y_OFFSET. Example: --crop 500 500 100 100")
@click.option('--grayscale', is_flag=True, help="Convert the image to grayscale.")
@click.option('--brightness', type=float, help="Adjust brightness (-1.0 to 1.0). Default is 0.")
@click.option('--contrast', type=float, help="Adjust contrast (>1.0 for more contrast, <1.0 for less). Default is 1.")
@click.option('--saturation', type=float, help="Adjust saturation (0 for grayscale, >1 for vivid). Default is 1.")
@click.option("--quiet", is_flag=True, default=False,help="Quiet mode.")
@click.pass_context
def convert_image_format(ctx ,file_path, output_path, resize, crop, grayscale, brightness, contrast, saturation, quiet):
    """
    Convert an image format

    FILE_PATH: Path to the input image file.
    OUTPUT_PATH: Path to the output image file with the desired format.
    """
    # options do not add up
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        output_path = resolve_path(ctx.obj['workdir'], output_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    command = ["ffmpeg", "-i", file_path]
    filters = []

    # Add filters based on the options
    if resize:
        width, height = resize
        filters.append(f"scale={width}:{height}")

    if crop:
        width, height, x_offset, y_offset = crop
        filters.append(f"crop={width}:{height}:{x_offset}:{y_offset}")

    if grayscale:
        filters.append("format=gray")

    if brightness or contrast or saturation:
        filters.append(f"eq=brightness={brightness or 0}:contrast={contrast or 1}:saturation={saturation or 1}")

    # Combine all filters into a single -vf parameter
    if filters:
        filter_string = ",".join(filters)
        command.extend(["-vf", filter_string])

    if quiet:
        command.extend(["-loglevel", "quiet"])

    # Specify the output file
    command.append(output_path)

    # Execute the command
    try:
        subprocess.run(command, check=True)
        click.echo(f"Image successfully converted to {output_path}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to convert image format. {e}", err=True)


@module.command()
@click.argument('file_path', type=click.Path())
@click.argument('output_folder', type=click.Path())
@click.option('--fps', type=float, default=None, help="Frames per second to extract. If not specified, extracts all frames.")
@click.option('--frame-prefix', type=str, default="frame", help="Prefix for the extracted frame filenames. Default is 'frame'.")
@click.option('--format', type=str, default="png", help="Output image format (e.g., png, jpg, bmp). Default is 'png'.")
@click.option("--quiet", is_flag=True, default=False,help="Quiet mode.")
@click.pass_context
def extract_frames_gif(ctx,file_path, output_folder, fps, frame_prefix, format, quiet):
    """
    Extract frames from a GIF or animation using ffmpeg.

    FILE_PATH: Path to the input animated file (GIF or video).
    OUTPUT_FOLDER: Folder to save the extracted frames.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        output_folder = resolve_path(ctx.obj['workdir'], output_folder)
    except Exception as e:
        click.echo(e)
        sys.exit()


    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    output_path = os.path.join(output_folder, f"{frame_prefix}_%03d.{format}")
    command = ["ffmpeg", "-i", file_path]

    if fps:
        command.extend(["-vf", f"fps={fps}"])  # Add FPS filter

    if quiet:
        command.extend(["-loglevel", "quiet"])

    command.append(output_path)

    try:
        subprocess.run(command, check=True)
        click.echo(f"Frames successfully extracted to {output_folder}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to extract frames. {e}", err=True)


@module.command()
@click.argument('file_path', type=click.Path())
@click.argument('output_folder', type=click.Path())
@click.option('--fps', type=float, default=None, help="Frames per second to extract. If not specified, extracts all frames.")
@click.option('--start-time', type=str, default=None, help="Start time for extraction in format HH:MM:SS (e.g., 00:01:30 for 1 min 30 secs).")
@click.option('--end-time', type=str, default=None, help="End time for extraction in format HH:MM:SS (e.g., 00:02:00 for 2 mins).")
@click.option('--frame-prefix', type=str, default="frame", help="Prefix for the extracted frame filenames. Default is 'frame'.")
@click.option('--format', type=str, default="png", help="Output image format (e.g., png, jpg, bmp). Default is 'png'.")
@click.option('--resize', type=(int, int), help="Resize frames to WIDTH HEIGHT (e.g., --resize 1920 1080).")
@click.option('--grayscale', is_flag=True, help="Convert extracted frames to grayscale.")
@click.option("--quiet", is_flag=True, default=False,help="Quiet mode.")
@click.pass_context
def extract_frames_video(ctx, file_path, output_folder, fps, start_time, end_time, frame_prefix, format, resize, grayscale, quiet):
    """
    Extract frames from a video.

    INPUT_FILE: Path to the input video file.
    OUTPUT_FOLDER: Folder to save the extracted frames.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        output_folder = resolve_path(ctx.obj['workdir'], output_folder)
    except Exception as e:
        click.echo(e)
        sys.exit()

    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    output_path = os.path.join(output_folder, f"{frame_prefix}_%03d.{format}")
    command = ["ffmpeg", "-i", file_path]

    if start_time:
        command.extend(["-ss", start_time])  # Start time
    if end_time:
        command.extend(["-to", end_time])    # End time

    if fps:
        command.extend(["-vf", f"fps={fps}"])

    if resize:
        width, height = resize
        resize_filter = f"scale={width}:{height}"
        command.extend(["-vf", resize_filter])

    if grayscale:
        if "-vf" in command:
            command[-1] += ",format=gray"  # Append to existing filters
        else:
            command.extend(["-vf", "format=gray"])

    if quiet:
        command.extend(["-loglevel", "quiet"])
    # Specify the output path
    command.append(output_path)

    # Run the command
    try:
        subprocess.run(command, check=True)
        click.echo(f"Frames successfully extracted to {output_folder}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to extract frames. {e}", err=True)

@module.command()
@click.argument('file_path', type=click.Path())
@click.argument('output_file', type=click.Path())
@click.option('--audio-codec', type=str, default=None, help="Specify the audio codec (e.g., aac, mp3, pcm_s16le).")
@click.option('--bitrate', type=str, default=None, help="Set the audio bitrate (e.g., 128k for 128 kbps).")
@click.option('--start-time', type=str, default=None, help="Start time for extraction in format HH:MM:SS (e.g., 00:01:30 for 1 min 30 secs).")
@click.option('--end-time', type=str, default=None, help="End time for extraction in format HH:MM:SS (e.g., 00:02:30 for 2 mins 30 secs).")
@click.option('--channels', type=int, default=None, help="Set the number of audio channels (e.g., 1 for mono, 2 for stereo).")
@click.option('--sample-rate', type=int, default=None, help="Set the audio sample rate (e.g., 44100 for 44.1 kHz).")
@click.option("--quiet", is_flag=True, default=False,help="Quiet mode.")
@click.pass_context
def extract_audio(ctx,file_path, output_file, audio_codec, bitrate, start_time, end_time, channels, sample_rate, quiet):
    """
    Extract the audio track from a video file.

    FILE_PATH: Path to the input video file.
    OUTPUT_FILE: Path to the output audio file with the desired format.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        output_file = resolve_path(ctx.obj['workdir'], output_file)
    except Exception as e:
        click.echo(e)
        sys.exit()

    # Check if the input is a video or audio file
    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")

    # Build the ffmpeg command
    command = ["ffmpeg", "-i", file_path]

    if is_video:
        command.append("-vn")  # Remove video stream if input is a video

    if audio_codec:
        command.extend(["-c:a", audio_codec])

    if bitrate:
        command.extend(["-b:a", bitrate])

    if start_time:
        command.extend(["-ss", start_time])
    if end_time:
        command.extend(["-to", end_time])

    if channels:
        command.extend(["-ac", str(channels)])

    if sample_rate:
        command.extend(["-ar", str(sample_rate)])

    if quiet:
        command.extend(["-loglevel", "quiet"])

    # Specify the output file
    command.append(output_file)

    try:
        subprocess.run(command, check=True)
        click.echo(f"Audio successfully extracted to {output_file}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to extract audio. {e}", err=True)


@module.command()
@click.argument('file_path', type=click.Path())
@click.argument('output_file', type=click.Path())
@click.option('--codec', type=str, default=None, help="Specify the codec for encoding (e.g., libx264, libx265, vp9).")
@click.option('--bitrate', type=str, default=None, help="Set the video bitrate (e.g., 1M for 1 Mbps).")
@click.option('--fps', type=float, default=None, help="Set the output frame rate.")
@click.option('--start-time', type=str, default=None, help="Start time for conversion in format HH:MM:SS (e.g., 00:01:30 for 1 min 30 secs).")
@click.option('--end-time', type=str, default=None, help="End time for conversion in format HH:MM:SS (e.g., 00:02:30 for 2 mins 30 secs).")
@click.option('--resize', type=(int, int), help="Resize the video to WIDTH HEIGHT (e.g., --resize 1280 720).")
@click.option('--grayscale', is_flag=True, help="Convert the video to grayscale.")
@click.option("--quiet", is_flag=True, default=False,help="Quiet mode.")
@click.pass_context
def convert_video(ctx, file_path, output_file, codec, bitrate, fps, start_time, end_time, resize, grayscale, quiet):
    """
    Convert a video to another format.

    FILE_PATH: Path to the input video file.
    OUTPUT_FILE: Path to the output video file with the desired format.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        output_file = resolve_path(ctx.obj['workdir'], output_file)
    except Exception as e:
        click.echo(e)
        sys.exit()


    # Build the ffmpeg command
    command = ["ffmpeg", "-i", file_path]

    if codec:
        command.extend(["-c:v", codec])

    if bitrate:
        command.extend(["-b:v", bitrate])

    if fps:
        command.extend(["-r", str(fps)])

    if start_time:
        command.extend(["-ss", start_time])
    if end_time:
        command.extend(["-to", end_time])

    if resize:
        width, height = resize
        resize_filter = f"scale={width}:{height}"
        command.extend(["-vf", resize_filter])

    if grayscale:
        if "-vf" in command:
            command[-1] += ",format=gray"  # Append to existing filters
        else:
            command.extend(["-vf", "format=gray"])

    if quiet:
        command.extend(["-loglevel", "quiet"])

    # Specify the output file
    command.append(output_file)

    # Run the command
    try:
        subprocess.run(command, check=True)
        click.echo(f"Video successfully converted to {output_file}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to convert video. {e}", err=True)


@module.command()
@click.argument('file_path', type=click.Path())
@click.argument('output_file', type=click.Path())
@click.option('--audio-codec', type=str, default=None, help="Specify the audio codec (e.g., aac, mp3, pcm_s16le).")
@click.option('--bitrate', type=str, default=None, help="Set the audio bitrate (e.g., 128k for 128 kbps).")
@click.option('--sample-rate', type=int, default=None, help="Set the audio sample rate (e.g., 44100 for 44.1 kHz).")
@click.option('--channels', type=int, default=None, help="Set the number of audio channels (e.g., 1 for mono, 2 for stereo).")
@click.option('--start-time', type=str, default=None, help="Start time for conversion in format HH:MM:SS (e.g., 00:01:30 for 1 min 30 secs).")
@click.option('--end-time', type=str, default=None, help="End time for conversion in format HH:MM:SS (e.g., 00:02:30 for 2 mins 30 secs).")
@click.option('--normalize', is_flag=True, help="Normalize audio levels for forensic clarity.")
@click.option('--remove-noise', is_flag=True, help="Apply basic noise reduction using an audio filter.")
@click.option("--quiet", is_flag=True, default=False,help="Quiet mode.")
@click.pass_context
def convert_audio(ctx, file_path, output_file, audio_codec, bitrate, sample_rate, channels, start_time, end_time, normalize, remove_noise, quiet):
    """
    Convert audio files from one format to another with forensic-focused options.

    FILE_PATH: Path to the input audio file.
    OUTPUT_FILE: Path to the output audio file with the desired format.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        output_file = resolve_path(ctx.obj['workdir'], output_file)
    except Exception as e:
        click.echo(e)
        sys.exit()

    # Build the ffmpeg command
    command = ["ffmpeg", "-i", file_path]

    if audio_codec:
        command.extend(["-c:a", audio_codec])

    if bitrate:
        command.extend(["-b:a", bitrate])

    if sample_rate:
        command.extend(["-ar", str(sample_rate)])

    if channels:
        command.extend(["-ac", str(channels)])

    if start_time:
        command.extend(["-ss", start_time])
    if end_time:
        command.extend(["-to", end_time])

    if normalize:
        if "-af" in command:
            command[-1] += ",dynaudnorm"
        else:
            command.extend(["-af", "dynaudnorm"])

    if remove_noise:
        if "-af" in command:
            command[-1] += ",anlmdn=s=20"
        else:
            command.extend(["-af", "anlmdn=s=20"])  # Adjust noise threshold as needed

    if quiet:
        command.extend(["-loglevel", "quiet"])

    # Specify the output file
    command.append(output_file)

    try:
        subprocess.run(command, check=True)
        click.echo(f"Audio successfully converted to {output_file}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Failed to convert audio. {e}", err=True)


@module.command()
@click.argument('file_path', type=click.Path())
@click.option('--output_dir', type=click.Path(), default="extraction_output", help="Directory to save extracted files. Default is 'binwalk_output'.")
@click.option('--depth', type=int, default=0, help="Limit the depth of extraction. Default is 0 (current dir).")
@click.option('--quiet', is_flag=True, help="Suppress binwalk's verbose output.")
@click.pass_context
def extract_embedded_files(ctx, file_path, output_dir, depth, quiet):
    """
        Extract embedded files from a given FILE_PATH.

        FILE_PATH: Path to the file to analyze and extract embedded files from.
        """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
        if output_dir:
            output_dir = resolve_path(ctx.obj['workdir'], output_dir)
    except Exception as e:
        click.echo(e)
        sys.exit()

    command = ["binwalk", "--extract", "-M", file_path]

    if depth > 0:
        command.extend(["--depth", str(depth)])

    if output_dir:
        command.extend(["--directory", output_dir])

    if quiet:
        command.append("--quiet")

    try:
        subprocess.run(command, check=True)
        click.echo(f"Embedded files successfully extracted")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error extracting embedded files: {e.stderr}", err=True)


@module.command()
@click.argument('dir_path', type=click.Path())
@click.option("--depth", type=int, default=0, help="Limit the depth of extraction. Default is 0 (current dir).")
@click.pass_context
def search_embedded_files(ctx, dir_path, depth):
    """
    Search embedded files from a given DIR_PATH.

    DIR_PATH: Path to the directory to search embedded files from.
    """

    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], dir_path, has_to_be_file=False)
        dir_path = resolve_path(ctx.obj['workdir'], dir_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    for root, dirs, files in os.walk(dir_path):
        # Limit recursion to the specified depth

        if depth is not None:
            current_depth = root[len(dir_path):].count(os.sep)
            if current_depth >= depth:
                dirs[:] = []  # Do not recurse further

        for file in files:
            file_path = os.path.join(root, file)
            if _is_embedded_file(file_path):
                click.echo(f"- {file_path}")


@module.command()
@click.argument('file_path', type=click.Path())
@click.pass_context
def embedded_file_content(ctx, file_path):
    """
    Prints out the content of an embedded file.

    FILE_PATH: Path to the embedded file.
    """
    try:
        # Validate input paths
        check_path_type(ctx.obj['workdir'], file_path, has_to_be_file=True)
        file_path = resolve_path(ctx.obj['workdir'], file_path)
    except Exception as e:
        click.echo(e)
        sys.exit()

    result = run_command(["binwalk", file_path])
    click.echo(result)
#-------------help functions-------------

def _is_embedded_file(file_path):

    try:
        #Step 1
        if _is_archive_file(file_path):
            return True

        # Step 2:
        binwalk_result = run_command(["binwalk", file_path])
        lines = binwalk_result.splitlines()
        embedded_files = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ["tif", "tiff"]):  # Exclude common false positives
                continue

            if line.strip() and line.split()[0].isdigit():  # Lines with offsets indicate file signatures
                embedded_files.append(line)

        # If more than 2 distinct embedded files are found, consider it an embedded file
        if len(embedded_files) > 2:
            return True

        return False
    except subprocess.CalledProcessError as e:
        click.echo(f"Error analyzing file '{file_path}': {e.stderr}", err=True)
        return False


def _is_archive_file(file_path):
    """
    Check if the file is a common archive type (e.g., ZIP, TAR, RAR, 7z).
    """
    archive_signatures = {
        b'PK': 'ZIP archive',
        b'Rar!': 'RAR archive',
        b'\x1F\x8B': 'GZIP archive',
        b'BZh': 'BZIP2 archive',
        b'7z\xBC\xAF\x27\x1C': '7z archive',
        b'ustar': 'TAR archive',
        b'POSIX': 'TAR archive'
    }

    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)  # Read the first 8 bytes of the file

        for signature, description in archive_signatures.items():
            if header.startswith(signature):
                return True

    except Exception as e:
        click.echo(f"Error checking for archive type: {e}", err=True)

    return False