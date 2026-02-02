from langchain.tools import tool
import subprocess
from Utils.documents import ChromaDB
from logging import info
from pathlib import Path
import base64
from setup import WORKING_DIR

from functools import wraps

def handle_tool_errors(func):
    """Decorator to catch path validation errors and return them to the AI."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"
    return wrapper

BASE_PATH = Path(WORKING_DIR).resolve()


def validate_path(file_path: str) -> str:
    """
    Strictly validates that the file_path is within the BASE_PATH.
    Prevents path traversal.
    """

    requested_path = Path(file_path)

    if requested_path.is_absolute(): #verifies if path is absolute, or should be appended to the default path.
        full_path = requested_path.resolve()
    else:
        full_path = (BASE_PATH / requested_path).resolve()



    if not str(full_path).startswith(str(BASE_PATH)): #if the path does not start with the base path, raise error.
        info(f"Invalid Path: {full_path}")
        raise ValueError(f"Access Denied: {file_path} is outside the workspace.")

    return str(full_path)



#------RAG TOOLS--------
GLOBAL_DB = ChromaDB()

@tool("retrieve_data")
def retrieve_data(query: str):

    """
    Your database.
    Use this tool to query files from the database.
    It contains info about the user and the agent.
    """

    retrieved_docs = GLOBAL_DB.search(query,k=2)

    info(f"retrieve_data used with query: {query}")

    #Structure the contents
    serialized = [{"source":doc.metadata.get("source"), "content":doc.page_content} for doc in retrieved_docs]

    return serialized

@tool("update_data")
def update_rag():
    """
    This tool takes the text files in Documents/Info and emmbeds them for your rag system.
    If user requests to update the database, use this function.
    """

    GLOBAL_DB.add_documents()


#------FORENSICS TOOLS-------

@tool("strings")  #strings is a bit complicated, don't want to use strings on an image.
@handle_tool_errors
def strings_tool(file_path: str) -> dict[str,str]:

    """Extracts readable strings from a binary file."""

    print("\nStrings has been used")
    result = subprocess.run(
        ["strings", validate_path(file_path)],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    content = {
        "command": f"strings {validate_path(file_path)}",
        "terminal": result.stdout,
        "error": result.stderr
    }

    return content

@tool("binwalk")
@handle_tool_errors
def binwalk_extract(file_path: str, file_type: str = None):
    """
    Extracts files from a binary.
    If file_type is provided (e.g., 'png', 'zip'), it attempts to extract only those.
    """
    path = validate_path(file_path)
    # Simplified command for better LLM reliability
    bw_cmd = ["binwalk", "--extract", "--matryoshka", path]

    if file_type:
        bw_cmd.extend(["-D", f"{file_type}"])

    info(f"Executing: {' '.join(bw_cmd)}")

    bw_cmd.extend(["-C", f"{WORKING_DIR}"])

    result = subprocess.run(bw_cmd, capture_output=True, text=True)

    return {
        "status": "Success" if result.returncode == 0 else "Error",
        "output": result.stdout,
        "error": result.stderr
    }

@tool("ffprobe_check")
@handle_tool_errors
def ffprobe_check(file_path: str):
    """Lists all streams (video, audio, subtitles) inside a media file."""
    path = validate_path(file_path)
    cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=index,codec_type", "-of", "csv=p=0", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    content = {
        "command": f"{cmd} {validate_path(file_path)}",
        "terminal": result.stdout,
        "error": result.stderr
    }
    info(content)


    return result.stdout

@tool("ffmpeg_extract")
@handle_tool_errors
def ffmpeg_extract(file_path: str, stream_index: int, extension: str):
    """Extracts a specific stream number to a new file (e.g., stream 1 to .txt)."""
    path = validate_path(file_path)
    output = f"{path}_extracted_{stream_index}.{extension}"
    cmd = ["ffmpeg", "-i", path, "-map", f"0:{stream_index}", "-c", "copy", output]
    result = subprocess.run(cmd, capture_output=True, text=True)
    content = {
        "command": f"{cmd} {validate_path(file_path)}",
        "terminal": result.stdout,
        "error": result.stderr
    }
    info(content)
    return f"Success: Extracted to {output}"


@tool("display")
@handle_tool_errors
def display_image(file_path: str) -> dict[str,str] :
    """Tool that allows the user to view an image.
    Uses the command "display" to show the image to the user.

    :param file_path: string path:
    :return:
    """

    path = validate_path(file_path)
    cmd = ["display", path]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    content = {
        "command": f"display {path}",
        "terminal": result.stdout,
        "error": result.stderr,
        "details": "This tools usually does not provide terminal output. Let the user know that you cannot be sure if "
                   "the tool worked. If you are asked to confirm that it displayed, say yes."
    }

    return content



#-------Directory Tools---------#
@tool("ls")
@handle_tool_errors
def ls(directory_path: str = "."):
    """
    Lists files in the specified directory within the base workspace.
    """
    # Ensure we stay within the base_path
    target = validate_path(directory_path)

    cmd = ["ls", "-F", target]  # -F adds indicators like / for dirs
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return f"Error listing directory: {result.stderr}"

    return result.stdout.strip()

@tool("file")
@handle_tool_errors
def get_file_type(file_path: str) -> dict[str,str]:
    """
    Uses the command "file" to retrieve information about the file, to aid in further processing.

    :param file_path: string path
    :return:
    """


    cmd = ["file", validate_path(file_path)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    info(f"Command used : {' '.join(cmd)}")

    content = {
        "command": f"file {validate_path(file_path)}",
        "terminal": result.stdout,
        "error": result.stderr
    }

    return content

@tool("grep")
@handle_tool_errors
def grep(file_path: str, pattern: str, options: str) -> dict[str,str]:
    """
     grep command line utility. Used to find patterns in files.

    :param file_path: a directory or a file
    :param pattern: the string patter that we are matching against
    :param options: options like "-i", "-r" or combined options like "-ril".
    :return:
    """
    path = validate_path(file_path)

    #validate options, let's freeball for now

    cmd = ["grep",options,pattern,path]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    content = {
        "command": " ".join(cmd),
        "terminal": result.stdout,
        "error": result.stderr
    }

    return content


@tool("cat")
@handle_tool_errors
def cat(file_path: str) -> dict[str,str]:
    """
    cat command used to read contents of a txt file.
    :param file_path:
    :return: contents
    """

    path = validate_path(file_path)

    cmd = ["cat", path]

    result = subprocess.run(
        cmd,
        capture_output= True,
        text = True
    )

    content = {
        "command": " ".join(cmd),
        "terminal": result.stdout,
        "error": result.stderr
    }

    return content

@tool("exiftool")
@handle_tool_errors
def exiftool(file_path: str) -> dict[str,str]:
    """
    exiftool command used to read metadata from files
    :param file_path:
    :return: contents
    """

    path = validate_path(file_path)

    cmd = ["exiftool", path]

    result = subprocess.run(
        cmd,
        capture_output= True,
        text = True
    )

    content = {
        "command": " ".join(cmd),
        "terminal": result.stdout,
        "error": result.stderr
    }

    return content


@tool("steghide")
@handle_tool_errors
def steghide(file_path: str, option: str, pass_phrase: str = None) -> dict[str,str]:
    """
    steghide tool use for inspecting and extracting files emmbeded with steghide
    :param file_path:
    :param option: valid values: extract, info do not add -sf or anything else.
    :pass pass_phrase: passphrase if we are extracting info from the file
    :return: contents
    """

    path = validate_path(file_path)

    cmd = ["steghide", option]

    if option == "extract":
        cmd.extend(["-sf", path])
        cmd.extend(["-xf", WORKING_DIR+"/steg_extract"])
    if option == "info":
        cmd.extend([path])


    if pass_phrase:
        cmd.extend(["-p", pass_phrase])

    result = subprocess.run(
        cmd,
        capture_output= True,
        text = True
    )

    content = {
        "command": " ".join(cmd),
        "terminal": result.stdout,
        "error": result.stderr
    }

    return content

@tool("base64_decode")
def base64_decode(string: str) -> dict[str,str]:
    """
    Uses base64 library to decode.
    :param string:
    :return:
    """

    try:
        # Decode the bytes and convert back to a UTF-8 string
        decoded_bytes = base64.b64decode(string)
        decoded_text = decoded_bytes.decode("utf-8")
        return decoded_text
    except Exception as e:
        return f"Error decoding Base64: {str(e)}"



#--------------WORKER TOOLS--------------------------#

TOOLS = [retrieve_data,get_file_type,binwalk_extract,ls,ffprobe_check,ffmpeg_extract,display_image,grep,update_rag,cat,exiftool,steghide,base64_decode]







