import sys
import os
import re

#pip install PyQt5
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QFileDialog, 
    QPushButton, 
    QMessageBox
)
from PyQt5.QtMultimedia import QSound
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from tensorflow import keras
from PIL import Image
import numpy as np




class Pokedex(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pokédex")
        self.setFixedSize(735, 559)

        # Create a background for the windows 
        bg = QLabel(self)
        pix = QPixmap("./pokedex.png")
        bg.setPixmap(pix)
        bg.setGeometry(0, 0, pix.width(), pix.height()) # The bg will take all the space 
        bg.lower()
        
        self.images_size = (0,0)
        
        self.images = []
        self.current_index = 0
        self.cnn = None
        self.pokedex = ["Bulbasaur", "Charmander", "Pikachu","Squirtle"]

        # Style of the directionnal buttons
        arrow_btn_style = """ 
            QPushButton {
                color: red;
                background-color: transparent;
                border: none;
                font-size: 20px;
            }
            QPushButton:hover {
                color: white;
            }
        """

        btn_style = """ 
            QPushButton {
                color: white;
                background-color: transparent;
                border : none;
            }
            QPushButton:hover {
                color: red;
            }
        """
        label_style = """
            QLabel {
                color: white;
                background-color: transparent;
            }

        """

        label_style2 = """
            QLabel {
                color: white;
                background-color: transparent;
                font-size: 30px;
            }

        """
        
        # Buttons 
        self.prev_btn = QPushButton("<", self)
        self.prev_btn.setCursor(Qt.PointingHandCursor)# Icone of the mouse will change if hover
        self.prev_btn.setFocusPolicy(Qt.NoFocus) # no rectangle if we click on the button 
        self.prev_btn.clicked.connect(self.prevImage)
        self.prev_btn.setFlat(True) # remove the bg and border
        self.prev_btn.setStyleSheet(arrow_btn_style)
        self.prev_btn.setGeometry(245, 410, 50, 50)
        
        self.next_btn = QPushButton(">", self)
        self.next_btn.setCursor(Qt.PointingHandCursor) 
        self.next_btn.setFocusPolicy(Qt.NoFocus)
        self.next_btn.clicked.connect(self.nextImage)
        self.next_btn.setFlat(True)
        self.next_btn.setStyleSheet(arrow_btn_style)
        self.next_btn.setGeometry(300, 410, 50, 50)

        self.drop_zone = ClickZone(self)
        self.drop_zone.setCursor(Qt.OpenHandCursor)
        self.drop_zone.setGeometry(92, 188, 217, 142)

        # Model button 

        self.model_btn = QPushButton("Choose Model", self)
        self.model_btn.setGeometry(435, 458, 120, 30)
        self.model_btn.setCursor(Qt.PointingHandCursor)
        self.model_btn.setFocusPolicy(Qt.NoFocus)
        self.model_btn.setAutoDefault(False)
        self.model_btn.setDefault(False)
        self.model_btn.setFlat(True) # remove the bg and border
        self.model_btn.clicked.connect(self.selectModel)
        self.model_btn.setStyleSheet(btn_style)

        # Label model 

        self.model_label = QLabel("Model : X", self)
        self.model_label.setGeometry(585, 458, 120, 30)
        self.model_label.setStyleSheet(label_style)

        # Predict button 

        self.predict_btn = QPushButton("ON", self)
        self.predict_btn.setGeometry(65, 382, 50, 50)
        self.predict_btn.setCursor(Qt.PointingHandCursor)
        self.predict_btn.setFocusPolicy(Qt.NoFocus)
        self.predict_btn.setAutoDefault(False)
        self.predict_btn.setDefault(False)
        self.predict_btn.setFlat(True) # remove the bg and border
        self.predict_btn.clicked.connect(self.predict)
        self.predict_btn.setStyleSheet(arrow_btn_style)

        # Label predict 

        self.predict_label = QLabel("", self)
        self.predict_label.setGeometry(460, 225, 200, 30)
        self.predict_label.setStyleSheet(label_style2)
        
        
        
    def prevImage(self): # Go back one slot if possible and reload that image
        print(self.current_index, len(self.images))
        self.predict_label.setText("") # Clear the pokemon prediction label
        if self.current_index != 0:
            self.current_index -= 1
            self.drop_zone.removeBackground()
            pix = self.images[self.current_index]
            self.drop_zone.loadImage(pix)

    
    def nextImage(self): # Advance to the next slot, clear if it’s a new slot.
        print(self.current_index, len(self.images))
        self.predict_label.setText("") # Clear the pokemon prediction label
        if self.current_index < len(self.images) :
            self.current_index += 1
            
            if self.current_index == len(self.images): # If the index egal the number of images, we need to clear the drop zone to prepare a new image 
                self.drop_zone.showBackground()
                self.drop_zone.setEnabledClick(True) # We can drop another pic

            else: # Else, a pic is already in this index so we recharge it 
                self.drop_zone.removeBackground()
                pix = self.images[self.current_index]
                self.drop_zone.loadImage(pix)

    def selectModel(self):
        model_path, _ = QFileDialog.getOpenFileName( # Let the user choose the model 
            self,
            "Select CNN model file",
            "./CNN_models",              
            "Keras Model (*.h5 *.keras)"
        )
        if not model_path:
            return

        try:
            self.cnn = keras.models.load_model(model_path)
            self.model_label.setText("Model : ✓")


            filename = os.path.basename(model_path)   # The name of the cnn "cnn_model_nxn.keras"
            m = re.search(r'(\d+)x(\d+)', filename) 
            self.images_size = (int(m.group(1)), int(m.group(2)))
            print(self.images_size)
            
        except Exception as e: # Error box
            QMessageBox.critical(
                self,
                "Error loading the CNN",
                f"Impossible to load the model :\n{e}"
            )

    def predict(self):
        if self.cnn is None:
            QMessageBox.warning(self, "No model",
                                "Please choose a CNN model first.")
            return
        if len(self.images) == 0 and self.current_index == len(self.images):
            QMessageBox.warning(self, "No image",
                                "Please load an image before predicting.")
            return

        try: # Try to open the image, resize and convert in rgb
            print(self.images[self.current_index])
            img = Image.open(self.images[self.current_index])
            img = img.resize(self.images_size)      # size of the images   
            img = img.convert('RGB')             
        except Exception as e:
            QMessageBox.critical(self, 
                                 "Load error",
                                 f"Cannot open image:\n{e}")
            return

        # Normalise and reshape it
        arr = np.asarray(img, dtype=np.float32) / 255.0  
        batch = np.expand_dims(arr, axis=0)       # shape (1,256,256,3)
    

        try:
            preds = self.cnn.predict(batch)
        except Exception as e:
            QMessageBox.critical(self, 
                                 "Prediction error",
                                 f"Prediction failed:\n{e}")
            return
            
        print(preds)
        idx   = np.argmax(preds[0])
        self.predict_label.setText(self.pokedex[idx])

    


class ClickZone(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)

        self.click_enabled = True

        self.bg_style = """
            background-image: url(./background.jpg);
            background-repeat: no-repeat;
            background-position: center;
            border-radius: 15px;
        """
        self.no_bg_style = """
            background-color: transparent;
        """
        
        self.showBackground()
        
    def setEnabledClick(self, yes: bool):
        self.click_enabled = yes
        self.setAcceptDrops(yes)


    def mousePressEvent(self, e): # Handle clicks as file open if dropping is enabled.
        print(self.click_enabled)
        if self.click_enabled and (e.button() == Qt.LeftButton):
            path, _ = QFileDialog.getOpenFileName(
                None, 
                "Choose an image",
                "./Images_test", 
                "Images (*.png *.jpg *.jpeg )"
            )
            if  path: 
                self.removeBackground() # Remove the background for the image 
                self.loadImage(path)
                self.setEnabledClick(False) # After dropping one image, deactivate the possibility to drop another here
                images = self.parent().images
                images.append(path) # Add the pic to the tab images 

    def loadImage(self, path):
        pix = QPixmap(path)
        pix = pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(pix)

    def showBackground(self): # Clear any image and show the drop prompt background
        self.clear()            
        self.setStyleSheet(self.bg_style)

    def removeBackground(self): # Remove the prompt background so the image will show cleanly.
        self.clear()            
        self.setStyleSheet(self.no_bg_style)

        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Pokedex()
    w.show()
    sys.exit(app.exec_())