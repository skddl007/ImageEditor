from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from PIL import Image, ImageFilter
from io import BytesIO
import base64
import os
import cv2
import numpy as np
import pytesseract
import tempfile


app = Flask(__name__,static_folder='data')

# stack to store edit image
undostack = []
redostack = []

#---------------------------------------------------------------Editor function---------------------------------------------------------
def detect_faces(main_image):
    '''Function check in the image face is present or not if face in there the make a rectangle box on the face
       Parameters:
       - main_image: a image use for operaton
    '''
    
    img = cv2.cvtColor(np.array(main_image), cv2.COLOR_RGB2BGR)  # Convert PIL Image to OpenCV format
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
    pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))  # Convert back to PIL Image
    return pil_image


def extract_text_from_image(image_data):
    '''Function use to extrect text from the image if text in there using pytesseract module
    Parameters:
       - image_data: a image use for operaton
    Return:
        - text present on the image.   
    
    '''
    try:
        image = Image.open(BytesIO(image_data))
        text = pytesseract.image_to_string(image) 
        return text
    except Exception as e:
        return str(e)


#--------------------------------------------------------------------------------ROUTE-----------------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def portal():
    '''Main route which take image and store in a undostack'''
    # Here I make a clear undo and redo list clear for each new img
    undostack.clear()
    redostack.clear()
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
        
        if len(undostack) > 0:
            image_data = undostack[-1]  # Get the last uploaded image from the stack
            img_io = BytesIO()  # create a instance of BytesIO class
            image_data.save(img_io, format='JPEG')  # Save the image in JPEG format
            img_io.seek(0)  # Move the cursor to the beginning of the BytesIO object
            image_data = base64.b64encode(img_io.getvalue()).decode('utf-8')   # Encode the image data in base64 format and decode it to a UTF-8 string
            
            
            if request.method == 'POST':
                effect = request.form['effect']
                # print(effect)
                main_image = Image.open(BytesIO(base64.b64decode(image_data)))  # decode the image from base64 image data
                    
                if effect == 'rotate':
                    """
                        Rotate the image using the PIL module's rotate function.
                        Parameters:
                        - rotate_angle: The angle (in degrees) by which to rotate the image.
                        Returns:
                        - The rotated image is appended to the undo stack.
                    """
                    rotate_angle = int(request.form['rotate'])
                    image = main_image.rotate(rotate_angle)
                    undostack.append(image)     # store edited img in undostack

                elif effect == 'crop':
                    """
                    Crop the image using the PIL module's crop function, taking x and y coordinates as parameters.
                    Parameters:
                    - crop_size: The size of the crop box.
                    - x: The x-coordinate for cropping.
                    - y: The y-coordinate for cropping.
                    Returns:
                    - The cropped image is appended to the undo stack.
                    """
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
                        # store edited img in undostack
                        undostack.append(image)
                
                elif effect=='blur':
                    '''Apply BoxBlur filter to the image with given bule amount
                       Parameters:
                       - blur: The amount of blur to apply (0-99)
                       Return:
                       - The blurred image is appended to the undo stack'''
                       
                    blur_amount = int(request.form['blur'])
                    blur_amount=blur_amount%100
                    image = main_image.filter(ImageFilter.BoxBlur(blur_amount))
                    # undustack append
                    undostack.append(image)

                elif effect == 'filter':
                    """
                    Apply a selected filter from a predefined list of filters to the main image.
                    Parameters:
                    - effect_option: The name of the filter selected by the user.
                    Returns:
                    - The filtered image is appended to the undo stack.
                    """
                    filter_name = request.form.get('effect_option')
                    # print(filter_name)
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
                    """
                    Detect faces in the main image using a face detection algorithm
                    """

                    image = detect_faces(main_image)
                    # undustack append
                    undostack.append(image)
                
                elif effect == 'extract_text':
                    """Extract text from an image using OCR (Optical Character Recognition)"""
                    text = extract_text_from_image(base64.b64decode(image_data))
                    flash("Extracted Text: " + text)
                       
                elif effect == 'undu':
                    """If image in undostack than it pop and append in redostack"""
                    if len(undostack) > 0:
                        image = undostack.pop()
                        redostack.append(image)
                        print('redu', len(redostack))

                elif effect == 'redu' and len(redostack) > 0:
                    """If image in redostack than it pop and append in undostack"""
                    image = redostack.pop()
                    undostack.append(image)
                    print('undu', len(undostack))

                elif effect == 'reset':
                    image = undostack[0]
                    undostack.clear()
                    redostack.clear()
                    undostack.append(image)
                    
                if image is not None:
                    # Another stuff
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
            # Here I make a clear undo and redo list clear for each new img
            undostack.clear()
            redostack.clear()
            return render_template('image_inpu.html')
    except:
        return render_template('image_editor.html',image_data=image_data,unducount=unducount,total=total)
    
    
# dawonload
@app.route('/download')
def download():
    """ 
    Try to download the last edited image from the undo stack. If no edited image is available, redirect to the portal
    """
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

if __name__ == '__main__':
    app.run(debug=True)
