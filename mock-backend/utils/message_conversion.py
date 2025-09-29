
import urllib

"""
private async fileToBase64DataURL(file: File): Promise<string> {
    // Extract to base64 with filename added
    // Example
    "data:text/csv;base64,TmFtZSxBZ2UsQnJlZWQsQ29sb3IKQnVkZHksMyxHb2xkZW4gUmV0cmlldmVyLEdvbGRlbgpNYXgsNSxHZXJtYW4gU2hlcGhlcmQsQmxhY2sgYW5kIFRhbgpCYWlsZXksMixMYWJyYWRvciBSZXRyaWV2ZXIsQ2hvY29sYXRlCkx1Y3ksNCxCZWFnbGUsVHJpLWNvbG9yCkNoYXJsaWUsNixQb29kbGUsV2hpdGUKRGFpc3ksMSxCdWxsZG9nLEJyb3duIGFuZCBXaGl0ZQpDb29wZXIsNyxTaWJlcmlhbiBIdXNreSxHcmF5IGFuZCBXaGl0ZQpNb2xseSw0LERhY2hzaHVuZCxSZWQKUm9ja3ksMixCb3hlcixGYXduCkJlbGxhLDUsWW9ya3NoaXJlIFRlcnJpZXIsQmxhY2sgYW5kIFRhbg==,filename:dogs%20data.csv"

    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = () => {
        resolve(`${reader.result},filename:${encodeURIComponent(file.name)}`);
      };

      reader.onerror = (error) => {
        reject(error);
      };

      reader.readAsDataURL(file); // Read the file as a Data URL
    });
  }
import urllib.parse
 
 
"""

def decode_file_attachment(data_url: str) -> dict:
    """Decode base64 data URL to dictionary with mimetype, base64data, filename."""
    if not data_url.startswith("data:"):
        raise ValueError("Invalid data URL format")

    parts = data_url.split(",")
    if len(parts) < 2:
        raise ValueError("Invalid data URL format")

    header = parts[0]
    base64data = parts[1]

    # Parse mimetype from header
    if ":" not in header or ";" not in header.split(":", 1)[1]:
        raise ValueError("Invalid header format")
    mimetype = header.split(":", 1)[1].split(";", 1)[0]

    filename = None
    if len(parts) > 2:
        filename_part = parts[2]
        if filename_part.startswith("filename:"):
            encoded_filename = filename_part[9:]
            filename = urllib.parse.unquote(encoded_filename)

    return {
        "mimetype": mimetype,
        "base64data": base64data,
        "filename": filename
    }

def from_assistant_ui_contents_to_langgraph_contents(message: list[any]) -> dict:
    """Convert an Assistant UI message to a Langgraph message."""
    langgraph_contents = []

    for content in message:
        if content.get("type") == "text":
            langgraph_contents.append({
                "type": "text",
                "text": content.get("text", "")
            })
            continue

        if content.get("type") == "file":
            file_data = decode_file_attachment(content.get("data"))
            langgrapH_content = {
                "type": "file",
                "source_type": "base64",
                "filename": file_data["filename"],
                "mime_type": file_data["mimetype"],
                "data": file_data["base64data"]
            }
            langgraph_contents.append(langgrapH_content)
            continue

        if content.get("type") == "image":
            file_data = decode_file_attachment(content.get("image"))
            langgraph_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{file_data['mimetype']};base64,{file_data['base64data']}",
                },
            }
            langgraph_contents.append(langgraph_content)
            continue
    
    return langgraph_contents