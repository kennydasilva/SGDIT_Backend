from django.http import StreamingHttpResponse, Http404
from django.conf import settings
import os

def servir_video(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)

    if not os.path.exists(file_path):
        raise Http404("Vídeo não encontrado")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)

    if range_header:
        byte1, byte2 = 0, None
        match = range_header.replace("bytes=", "").split("-")
        if match[0]:
            byte1 = int(match[0])
        if match[1]:
            byte2 = int(match[1])

        length = file_size - byte1 if byte2 is None else byte2 - byte1 + 1

        with open(file_path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        response = StreamingHttpResponse(data, status=206, content_type='video/mp4')
        response['Content-Range'] = f'bytes {byte1}-{byte1 + length - 1}/{file_size}'
        response['Accept-Ranges'] = 'bytes'
        response['Content-Length'] = str(length)
        return response

    return StreamingHttpResponse(open(file_path, 'rb'), content_type='video/mp4')