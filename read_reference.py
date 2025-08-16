import docx

def read_docx(file_path):
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

if __name__ == '__main__':
    file_path = '/Users/wenxie/Documents/GitHub/niw/Reference_for_WenXie_Zhu.docx'
    text = read_docx(file_path)
    print(text) 