# Importation des modules nécessaires pour le CNN et la manipulation des données
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam

import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator, img_to_array, load_img
from PIL import Image
from tqdm import tqdm
import shutil

import requests
from io import BytesIO

# Chemin vers le dossier principal du projet
PATH = './'
# Taille à laquelle toutes les images seront redimensionnées
Image_size = 32

class CNNModel:
    def __init__(self, input_shape=(Image_size, Image_size, 3), num_classes=4):
        self.input_shape = input_shape
        self.num_classes = num_classes

    # Architecture CNN simple avec 3 couches convolutives + denses
    def build(self):
        model = Sequential([
            Conv2D(32, (3, 3), activation='relu', input_shape=self.input_shape),
            MaxPooling2D(2, 2),

            Conv2D(64, (3, 3), activation='relu'),
            MaxPooling2D(2, 2),

            Conv2D(128, (3, 3), activation='relu'),
            MaxPooling2D(2, 2),

            Flatten(),
            Dense(128, activation='relu'),
            Dropout(0.5),
            Dense(self.num_classes, activation='softmax') # Softmax pour la classification multiclasses
        ])

        # Compilation du modèle avec Adam et entropie croisée catégorique
        model.compile(optimizer=Adam(),
                      loss='categorical_crossentropy',
                      metrics=['accuracy'])
        return model

class CNNTrainer:

    def __init__(self, model=None, img_height=Image_size, img_width=Image_size, pixels=255, batch_size=64):
        self.IMG_HEIGHT = img_height
        self.IMG_WIDTH = img_width
        self.PIXELS = pixels
        self.BATCH_SIZE = batch_size
        self.model_builder = model
        self.model = None

        # Générateurs Keras pour chargement des données
        self.train_generator = None
        self.val_generator = None
        self.test_generator = None

    # Redimensionne toutes les images
    def resize_folder_images(self, folder_path_input, folder_path_output):
        
        os.makedirs(folder_path_output, exist_ok=True)

        for class_dir in os.listdir(folder_path_input):
            class_path = os.path.join(folder_path_input, class_dir)
            if os.path.isdir(class_path):
                output_class_dir = os.path.join(folder_path_output, class_dir)
                os.makedirs(output_class_dir, exist_ok=True)

                for filename in os.listdir(class_path):
                    img_path = os.path.join(class_path, filename)
                    try:
                        with Image.open(img_path) as img:
                            img = img.resize((self.IMG_HEIGHT, self.IMG_WIDTH)).convert('RGB')
                            output_filename = os.path.splitext(filename)[0] + ".jpg"
                            img.save(os.path.join(output_class_dir, output_filename), format="JPEG")
                    except Exception as e:
                        print(f"Erreur avec l'image {img_path}: {e}")
        print("Redimensionnement terminée dans :", folder_path_output)

    # Augmente chaque image du dossier source en générant des variantes transformées
    def augment_data_and_save(self, source_dir, target_dir, augmentations_per_image=2, color=True):
        datagen = ImageDataGenerator(
            rotation_range=30,
            width_shift_range=0.2,
            height_shift_range=0.2,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True,
            fill_mode='nearest'
        )

        os.makedirs(target_dir, exist_ok=True)

        for class_name in tqdm(os.listdir(source_dir)):
            source_class_dir = os.path.join(source_dir, class_name)
            if not os.path.isdir(source_class_dir):
                continue

            target_class_dir = os.path.join(target_dir, class_name)
            os.makedirs(target_class_dir, exist_ok=True)

            for filename in os.listdir(source_class_dir):
                img_path = os.path.join(source_class_dir, filename)
                try:
                    if color:
                        img = load_img(img_path, color_mode='rgb')
                    else:
                        img = Image.open(img_path).convert('L').convert('RGB')

                    x = img_to_array(img)
                    x = np.expand_dims(x, axis=0)

                    i = 0
                    for batch in datagen.flow(x, batch_size=1,
                                              save_to_dir=target_class_dir,
                                              save_prefix="aug",
                                              save_format="jpeg"):
                        i += 1
                        if i >= augmentations_per_image:
                            break
                except Exception as e:
                    print(f"Erreur avec l'image {img_path}: {e}")
        print("Augmentation terminée dans :", target_dir)

    # Sépare les images en trois sous-dossiers (train, val, test)
    def split_dataset_into_three(self, source_dir, output_base_dir, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Les ratios doivent faire 1"

        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(output_base_dir, split), exist_ok=True)

        for class_name in os.listdir(source_dir):
            class_path = os.path.join(source_dir, class_name)
            if not os.path.isdir(class_path):
                continue

            images = [f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))]
            train_and_val, test = train_test_split(images, test_size=test_ratio, random_state=42)
            train, val = train_test_split(train_and_val, test_size=val_ratio / (train_ratio + val_ratio), random_state=42)

            for split_name, split_data in zip(['train', 'val', 'test'], [train, val, test]):
                split_class_dir = os.path.join(output_base_dir, split_name, class_name)
                os.makedirs(split_class_dir, exist_ok=True)
                for filename in split_data:
                    shutil.copy2(os.path.join(class_path, filename), os.path.join(split_class_dir, filename))

        print("Séparation terminée dans :", output_base_dir)

    # Crée les générateurs Keras pour charger les données depuis les répertoires train/val/test.
    def prepare_generators(self, base_dir):
        datagen = ImageDataGenerator(rescale=1./self.PIXELS)

        self.train_generator = datagen.flow_from_directory(
            os.path.join(base_dir, 'train'),
            target_size=(self.IMG_HEIGHT, self.IMG_WIDTH),
            batch_size=self.BATCH_SIZE,
            class_mode='categorical'
        )

        self.val_generator = datagen.flow_from_directory(
            os.path.join(base_dir, 'val'),
            target_size=(self.IMG_HEIGHT, self.IMG_WIDTH),
            batch_size=self.BATCH_SIZE,
            class_mode='categorical'
        )

        self.test_generator = datagen.flow_from_directory(
            os.path.join(base_dir, 'test'),
            target_size=(self.IMG_HEIGHT, self.IMG_WIDTH),
            batch_size=self.BATCH_SIZE,
            class_mode='categorical',
            shuffle=False
        )

    # Construit le modèle CNN
    def build_model(self):
        num_classes = len(self.train_generator.class_indices)
        self.model_builder.num_classes = num_classes
        self.model_builder.input_shape = (self.IMG_HEIGHT, self.IMG_WIDTH, 3)
        self.model = self.model_builder.build()

    # Entraîne le modèle sur les données d'entraînement et le valide à chaque époque.
    def train(self, epochs=10):
        history = self.model.fit(
            self.train_generator,
            epochs=epochs,
            validation_data=self.val_generator
        )
        return history

    # Évalue les performances du modèle sur les données de test.
    def evaluate(self):
        loss, acc = self.model.evaluate(self.test_generator)
        print(f"Test Accuracy: {acc:.2f}")

    # Sauvegarde le modèle entraîné au format Keras
    def save_model(self, filename='cnn_model.keras'):
        self.model.save(filename)
        print(f"\nModèle enregistré sous {filename}\n")

    # Affiche les courbes d’évolution de la précision et de la perte.
    def plot_training(self, history):
        plt.figure(figsize=(12, 5))

        plt.subplot(1, 2, 1)
        plt.plot(history.history['accuracy'], label='Training Accuracy')
        plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
        plt.legend()
        plt.title('Accuracy over Epochs')

        plt.subplot(1, 2, 2)
        plt.plot(history.history['loss'], label='Training Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.legend()
        plt.title('Loss over Epochs')

        plt.show()

    # Affiche la matrice de confusion et les métriques de classification.
    def plot_confusion_matrix(self):
        predictions = self.model.predict(self.test_generator)
        y_pred = np.argmax(predictions, axis=1)
        y_true = self.test_generator.classes

        cm = confusion_matrix(y_true, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=self.test_generator.class_indices.keys())
        disp.plot(xticks_rotation=45)
        plt.title("Matrice de confusion")
        plt.show()

        print(classification_report(y_true, y_pred, target_names=self.test_generator.class_indices.keys()))

    # Prédit la classe d'une image à partir de son chemin local ou d'une URL.
    def predict_image(self, image_path_or_url):

        if image_path_or_url.lower().startswith(('http', 'https')):
            response = requests.get(image_path_or_url)
            img = Image.open(BytesIO(response.content))
        else:
            img = Image.open(image_path_or_url)

        img_resized = img.resize((self.IMG_HEIGHT, self.IMG_WIDTH)).convert('RGB')

        img_array = img_to_array(img_resized)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = img_array / self.PIXELS

        prediction = self.model.predict(img_array)

        predicted_class_index = np.argmax(prediction, axis=1)[0]

        class_names = list(self.train_generator.class_indices.keys())
        predicted_class_name = class_names[predicted_class_index]
        print(class_names)

        plt.figure(figsize=(6, 6))
        plt.imshow(img_resized)
        plt.title(f"Prédiction : {predicted_class_name}")
        plt.axis('off')
        plt.show()

        return predicted_class_name

if __name__ == "__main__":
    # Initialisation du modèle CNN
    cnn_model = CNNModel()
    # Création dy Trainer avec ce modèle
    trainer = CNNTrainer(model=cnn_model)
    
    # Resize des images (à faire une seule fois). Mettre vos images dans un dossier "Images_Pokemon"
    trainer.resize_folder_images(PATH + 'Images_Pokemon', PATH + 'Images_resized')
    
    
    # Augmentation (à faire une seule fois)
    trainer.augment_data_and_save( PATH + 'Images_resized', PATH + 'Images_augmented', augmentations_per_image=2, color=True)
    
    
    # Split (à faire une seule fois)
    trainer.split_dataset_into_three(PATH + 'Images_augmented', PATH + 'Images_split')
    
    # Préparation
    trainer.prepare_generators(PATH + 'Images_split')
    print("\n")
    # Construction, entraînement et évaluation
    trainer.build_model()
    
    history = trainer.train(epochs=10)
    print("\n")
    trainer.evaluate()


