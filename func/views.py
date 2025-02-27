from rest_framework.generics import GenericAPIView, UpdateAPIView
from rest_framework.response import Response
from .models import Draft, Saved
from .serializers import DraftSerializer, SavedSerializer
from rest_framework import response, status
from ftplib import FTP


class GetAllDraft(GenericAPIView):

    def get(self, request):
        model = Draft.objects.all()
        serializer = DraftSerializer(model, many=True)
        return Response(serializer.data)


class GetSingleDraft(GenericAPIView):

    def get(self, request, id):
        draft = Draft.objects.get(id=id)
        serializer = DraftSerializer(draft)
        return Response(serializer.data)


class AddDraft(GenericAPIView):
    serializer_class = DraftSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return response.Response({'message': "File saved as draft"}, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddSaved(GenericAPIView):
    serializer_class = SavedSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return response.Response({'message': "File saved !"}, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAllSaved(GenericAPIView):

    def get(self, request):
        model = Saved.objects.all()
        serializer = SavedSerializer(model, many=True)
        return Response(serializer.data)


class GetSingleSave(GenericAPIView):

    def get(self, request, id):
        save = Saved.objects.get(id=id)
        serializer = SavedSerializer(save)
        return Response(serializer.data)


from ftplib import FTP
from io import BytesIO


class FTPFileDataAPIView(GenericAPIView):
    def get(self, request, *args, **kwargs):
        FTP_HOST = "185.183.33.18"
        FTP_PORT = 4207  # Change to your FTP server's port
        FTP_USER = "ftpLedClip"
        FTP_PASS = ":)US8f76Sr"

        try:
            # Connect to the FTP server with port
            ftp = FTP()
            ftp.connect(FTP_HOST, FTP_PORT)
            ftp.login(FTP_USER, FTP_PASS)

            # Get list of files (excluding directories)
            files = ftp.nlst()
            file_data = {}

            for file in files:
                # Skip directories (optional: customize if needed)
                if "." not in file:  # Assuming files have an extension
                    continue

                # Read file content
                with BytesIO() as file_buffer:
                    ftp.retrbinary(f"RETR {file}", file_buffer.write)
                    file_buffer.seek(0)
                    file_data[file] = file_buffer.read().decode('utf-8', errors='ignore')  # Decode content

            # Close the connection
            ftp.quit()

            return Response({"status": "success", "files": file_data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
