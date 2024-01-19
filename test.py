import boto3
import PyPDF2
import io

bucket = 'first-challenge-team-5-admin-approval-bucket'

s3 = boto3.client(
        's3',
        aws_access_key_id= 'AKIARVTJVHQOSMFOIKD6',
        aws_secret_access_key='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',
    )


with open("output.pdf", "rb") as f:
    s3.upload_fileobj(f, bucket, 'object_output.pdf')

# def extract_folder_from_key(key):
#     # Split the key based on '/'
#     parts = key.split('/', 1)

#     # Extract the first part (folder)
#     if len(parts) > 0:
#         return parts[0]
#     else:
#         return ""

# def list_s3_objects(bucket_name):
#     s3 = boto3.client(
#         's3',
#         aws_access_key_id= 'AKIARVTJVHQOSMFOIKD6',
#         aws_secret_access_key='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',
#     )

#     # List all objects in the bucket
#     #response = s3.list_objects_v2(Bucket=bucket_name)
#     response1 = s3.get_object(Bucket=bucket_name, Key="KT/test3.pdf")
#     with response1['Body'] as binary_file:
#         content = binary_file.read()
#         # print(content)
#         pdf_file = PyPDF2.PdfReader(io.BytesIO(content))
#         for page_num in range(len(pdf_file.pages)):
#             page = pdf_file.pages[page_num]
#             text = page.extract_text()
#             print(f"{text}")
    
# if __name__ == "__main__":
#     list_s3_objects(bucket)
