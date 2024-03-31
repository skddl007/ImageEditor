from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from PIL import Image, ImageFilter
from io import BytesIO
import base64
import os
import cv2
import numpy as np
import pytesseract
import tempfile

app = Flask(__name__, static_folder='data')
app.secret_key = "This is secret"

# stack class
undostack = []
redostack = []

# Specify the full path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

#---------------------------------------------------------------Editor function---------------------------------------------------------
def rotate(main_image):
    rotate_angle = int(request.form['rotate'])
    image = main_image.rotate(rotate_angle)

# def crop(main_image,x,y,x0,y0,crop_size):
#     if x0>=x and y0>=y:
#         crop_left  = x
#         crop_upper = y
#         crop_right = x + crop_size
#         crop_lower = y + crop_size
#         image=main_image.crop((crop_left, crop_upper, crop_right, crop_lower))
#     return image

def blur(main_image,blur_amount):
    if blur_amount>100:
        blur_amount=blur_amount%100
    else:
        blur_amount=blur_amount
    image = main_image.filter(ImageFilter.BoxBlur(blur_amount))
    return image

def detect_faces(main_image):
    img = cv2.cvtColor(np.array(main_image), cv2.COLOR_RGB2BGR)  # Convert PIL Image to OpenCV format
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
    pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))  # Convert back to PIL Image
    return pil_image


def extract_text_from_image(image_data):
    try:
        image = Image.open(BytesIO(image_data))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return str(e)
    
# dawonload

@app.route('/download')
def download():
    try:
        if len(undostack) > 0:
            # Get the last edited image from the stack
            edited_image = undostack[-1]
            # Save the edited image to a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            edited_image.save(temp_file.name, format='JPEG')

            # Serve the temporary file for download
            return send_file(temp_file.name, as_attachment=True)
        else:
            # If no edited image is available, redirect to the portal
            return redirect(url_for('portal'))
    except Exception as e:
        return render_template('image_editor.html')

#------------------------------------------------------------------ROUTE-----------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def portal():
    try:
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return redirect(request.url)
            # Convert file to image
            image_data = Image.open(BytesIO(file.read()))
            undostack.append(image_data)
            return redirect(url_for('editor'))
    except Exception as e:
        print(e)
        # undostack=[]
        # redostack=[]
    return render_template('image_inpu.html')


# Route for the console page
@app.route('/editor', methods=['GET', 'POST'])
def editor():
    try:
        blur_amount=0
        unducount='0'
        reducount='0'  
        total=0
        messages=''
        # image_data=None # initialize image_data to None
        
        if len(undostack) > 0:
            image_data = undostack[-1]  # Get the last uploaded image from the stack
            img_io = BytesIO()
            image_data.save(img_io, format='JPEG')  # Save the image in JPEG format
            img_io.seek(0)  # Move the cursor to the beginning of the BytesIO object
            image_data = base64.b64encode(img_io.getvalue()).decode('utf-8')   # Encode the image data in base64 format and decode it to a UTF-8 string
            
            if request.method == 'POST':
                effect = request.form['effect']
                print(effect)
                main_image = Image.open(BytesIO(base64.b64decode(image_data)))
                    
                if effect == 'rotate':
                    rotate_angle = int(request.form['rotate'])
                    image = main_image.rotate(rotate_angle)
                    # undustack append
                    undostack.append(image)

                elif effect == 'crop':
                    crop_size = int(request.form['crop_size'])
                    x0, y0 = main_image.size
                    x=int(request.form['x'])
                    y=int(request.form['y'])
                    
                    # Calculate the crop box to maintain center crop
                    if x0>=x and y0>=y:
                        crop_left  = x
                        crop_upper = y
                        crop_right = x + crop_size
                        crop_lower = y + crop_size
                        # Crop the image
                        image = main_image.crop((crop_left, crop_upper, crop_right, crop_lower))
                        # undustack append
                        undostack.append(image)
                
                elif effect=='blur':
                    blur_amount = int(request.form['blur'])
                    blur_amount=blur_amount%100
                    image = main_image.filter(ImageFilter.BoxBlur(blur_amount))
                    # undustack append
                    undostack.append(image)
                elif effect == 'filter':
                    filter_name = request.form.get('effect_option')
                    print(filter_name)
                    lst=["BLUR", "CONTOUR", "DETAIL", "EDGE_ENHANCE", "EDGE_ENHANCE_MORE","EMBOSS", "FIND_EDGES", "SMOOTH", "SMOOTH_MORE", "SHARPEN"]
                    lst_filter = [ImageFilter.BLUR, ImageFilter.CONTOUR, ImageFilter.DETAIL, ImageFilter.EDGE_ENHANCE, 
                                  ImageFilter.EDGE_ENHANCE_MORE, ImageFilter.EMBOSS, ImageFilter.FIND_EDGES, ImageFilter.SMOOTH, ImageFilter.SMOOTH_MORE, ImageFilter.SHARPEN]
                    
                    # image = main_image
                    if filter_name in lst:
                        # Applying the blur filter
                        filter_obj = lst_filter[lst.index(filter_name)]    # Get the ImageFilter object
                        image = main_image.filter(filter_obj)
                    # undustack append
                    undostack.append(image)
                    
                elif effect == 'detect_faces':
                    image = detect_faces(main_image)
                    # undustack append
                    undostack.append(image)
                
                elif effect == 'extract_text':
                    text = extract_text_from_image(base64.b64decode(image_data))
                    flash("Extracted Text: " + text)
                       
                elif effect == 'undu':
                    if len(undostack) > 0:
                        image = undostack.pop()
                        redostack.append(image)
                        print('redu', len(redostack))

                elif effect == 'redu' and len(redostack) > 0:
                    image = redostack.pop()
                    undostack.append(image)
                    print('undu', len(undostack))

                elif effect == 'reset':
                    image = undostack[0]
                    undostack.clear()
                    redostack.clear()
                    undostack.append(image)
                    
                if image is not None:
                    # another stuff
                    edited_io = BytesIO()
                    image.save(edited_io, format='JPEG')
                    edited_io.seek(0)
                    image_data = base64.b64encode(edited_io.getvalue()).decode('utf-8')
                    # length of list
                    unducount=len(undostack)
                    reducount=len(redostack)
                    total=unducount+reducount
                    
            return render_template('image_editor.html', image_data=image_data,blur_amount=blur_amount,unducount=unducount,total=total,messages=messages)
        else:
            return render_template('image_inpu.html')
    except:
        return render_template('image_editor.html',image_data=image_data,unducount=unducount,total=total)

if __name__ == '__main__':
    app.run(debug=True)
