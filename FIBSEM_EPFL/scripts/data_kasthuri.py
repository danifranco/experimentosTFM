import numpy as np
import random
import pandas as pd
import os
import cv2
import keras
import sys
import math
from tqdm import tqdm
from skimage.io import imread, imshow
from sklearn.model_selection import train_test_split
from scipy.ndimage.interpolation import map_coordinates
from scipy.ndimage.filters import gaussian_filter
from PIL import Image
from texttable import Texttable
from keras.preprocessing.image import ImageDataGenerator as kerasDA

def load_data(train_path, train_mask_path, test_path, test_mask_path, 
              image_train_shape, image_test_shape, create_val=True, 
              val_split=0.1, seedValue=42):                                            
    """Load train, validation and test data from the given paths.       
                                                                        
       Args:                                                            
            train_path (str): path to the training data.                
            train_mask_path (str): path to the training data masks.     
            test_path (str): path to the test data.                     
            test_mask_path (str): path to the test data masks.          
            image_train_shape (array of 3 int): dimensions of the images.     
            image_test_shape (array of 3 int): dimensions of the images.     
            create_val (bool, optional): if true validation data is created.                                                    
            val_split (float, optional): % of the train data used as    
            validation (value between o and 1).                         
            seedValue (int, optional): seed value.                      
                                                                        
       Returns:                                                         
                X_train (numpy array): train images.                    
                Y_train (numpy array): train images' mask.              
                X_val (numpy array, optional): validation images 
                (create_val==True).
                Y_val (numpy array, optional): validation images' mask 
                (create_val==True).
                X_test (numpy array): test images.                      
                Y_test (numpy array): test images' mask.                
    """      
    
    print("\nLoading images . . .", flush=True)
                                                                        
    train_ids = sorted(next(os.walk(train_path))[2])                    
    train_mask_ids = sorted(next(os.walk(train_mask_path))[2])          
                                                                        
    test_ids = sorted(next(os.walk(test_path))[2])                      
    test_mask_ids = sorted(next(os.walk(test_mask_path))[2])            
                                                                        
    # Get and resize train images and masks                             
    X_train = np.zeros((len(train_ids), image_train_shape[1], 
                        image_train_shape[0], image_train_shape[2]),
                        dtype=np.uint8)                
    Y_train = np.zeros((len(train_mask_ids), image_train_shape[1], 
                        image_train_shape[0], image_train_shape[2]),
                        dtype=np.uint8) 
                                                                        
    print("\n[LOAD] Loading train images . . .", flush=True) 
    for n, id_ in tqdm(enumerate(train_ids), total=len(train_ids)):     
        img = imread(os.path.join(train_path, id_))                     
        if len(img.shape) == 3:
            img = img[:,:,0]    
        
        img = np.expand_dims(img, axis=-1)                              
        X_train[n] = img                                                
                                                                        
    print('\n[LOAD] Loading train masks . . .', flush=True)
    for n, id_ in tqdm(enumerate(train_mask_ids), total=len(train_mask_ids)):                      
        mask = imread(os.path.join(train_mask_path, id_))               
        if len(mask.shape) == 3:
            mask = mask[:,:,0]
        mask = np.expand_dims(mask, axis=-1)                            
        Y_train[n] = mask                                               
                                                                        
    Y_train = Y_train/255                                               
                                                                        
    # Get and resize test images and masks                              
    X_test = np.zeros((len(test_ids), image_test_shape[1], image_test_shape[0],   
                       image_test_shape[2]), dtype=np.uint8)                 
    Y_test = np.zeros((len(test_mask_ids), image_test_shape[1], 
                       image_test_shape[0], image_test_shape[2]), dtype=np.uint8) 
                                                                        
    print("\n[LOAD] Loading test images . . .", flush=True)
    for n, id_ in tqdm(enumerate(test_ids), total=len(test_ids)):       
        img = imread(os.path.join(test_path, id_))                      
        if len(img.shape) == 3:                                                 
            img = img[:,:,0]
        img = np.expand_dims(img, axis=-1)                              
        X_test[n] = img                                                 
                                                                        
    print("\n[LOAD] Loading test masks . . .", flush=True)
    for n, id_ in tqdm(enumerate(test_mask_ids), total=len(test_mask_ids)):                       
        mask = imread(os.path.join(test_mask_path, id_))                
        if len(mask.shape) == 3:
            mask = mask[:,:,0]
        mask = np.expand_dims(mask, axis=-1)                            
        Y_test[n] = mask                                                
                                                                        
    Y_test = Y_test/255                                                 
                                                                        
    if (create_val == True):                                            
        X_train, X_val, Y_train, Y_val = train_test_split(X_train, Y_train,
                                                          train_size=1-val_split,
                                                          test_size=val_split,
                                                          random_state=seedValue)      
 
        return X_train, Y_train, X_val, Y_val, X_test, Y_test           
    else:                                                               
        return X_train, Y_train, X_test, Y_test                         


def __foreground_percentage(mask, class_tag=1):
    """ Percentage of pixels that corresponds to the class in the given image.
        
        Args: 
            mask (numpy 2D array): image mask to analize.
            class_tag (int, optional): class to find in the image.
        Return:
            float: percentage of pixels that corresponds to the class. Value
            between 0 and 1.
    """

    c = 0
    for i in range(0, mask.shape[0]):
        for j in range(0, mask.shape[1]):     
            if mask[i][j] == class_tag:
                c = c + 1

    return (c*100)/(mask.shape[0]*mask.shape[1])


def crop_data(data, data_mask, width, height, force_shape=[0, 0], discard=False,
              d_percentage=0):                          
    """Crop data into smaller pieces                                    
                                                                        
       Args:                                                            
            data (4D numpy array): data to crop.                        
            data_mask (4D numpy array): data masks to crop.             
            width (str): output image width.
            height (str): output image height.
            force_shape (int tuple, optional): force horizontal and vertical 
            crops to the given numbers.
            d_percentage (int, optional): number between 0 and 100. The images 
            that have less foreground pixels than the given number will be 
            discarded.
                                                                        
       Returns:                                                         
            cropped_data (4D numpy array): cropped data images.         
            cropped_data_mask (4D numpy array): cropped data masks.     
            force_shape (int tuple): number of horizontal and vertical crops 
            made. Useful for future crop calls. 
    """                                                                 
                                                                        
    print("\nCropping [" + str(data.shape[1]) + ', ' + str(data.shape[2]) 
          + "] images into [" + str(width) + ', ' + str(height) + "] . . .", 
          flush=True)                                                  
    
    # Calculate the number of images to be generated                    
    if force_shape == [0, 0]:
        h_num = int(data.shape[1] / width) 
        if data.shape[1] % width > 0:
            h_num = h_num + 1
        v_num = int(data.shape[2] / height) 
        if data.shape[2] % height > 0:
            v_num = v_num + 1
        force_shape = [h_num, v_num]
    else:
        h_num = force_shape[0]
        v_num = force_shape[1]
        print("\n[CROP] Force crops to [" + str(h_num) + ", " + str(v_num) + "]",
              flush=True)

    total_cropped = data.shape[0]*h_num*v_num    

    # Resize data to adjust to a value divisible by height x width
    r_data = np.zeros((data.shape[0], h_num*height, v_num*width, data.shape[3]),      
                      dtype=np.uint8)    
    r_data[:data.shape[0],:data.shape[1],:data.shape[2]] = data                      
    r_data_mask = np.zeros((data.shape[0], h_num*height, v_num*width, 
                            data.shape[3]), dtype=np.uint8)                                   
    r_data_mask[:data_mask.shape[0],:data_mask.shape[1],
                :data_mask.shape[2]] = data_mask
    if data.shape != r_data.shape:
        print("\n[CROP] Resized data from " + str(data.shape) + " to " 
              + str(r_data.shape), flush=True)

    discarded = 0                                                                    
    cont = 0
    selected_images  = []

    # Discard images from the data set
    if discard == True:
        print("\n[CROP]: Selecting images to discard . . .", flush=True)
        for img_num in tqdm(range(0, r_data.shape[0])):                             
            for i in range(0, h_num):                                       
                for j in range(0, v_num):
                    p = __foreground_percentage(r_data_mask[img_num,
                                                            (i*width):((i+1)*height),
                                                            (j*width):((j+1)*height)])
                    if p > d_percentage: 
                        selected_images.append(cont)
                    else:
                        discarded = discarded + 1

                    cont = cont + 1

    # Crop data                                                         
    cropped_data = np.zeros(((total_cropped-discarded), height, width,     
                             r_data.shape[3]), dtype=np.uint8)
    cropped_data_mask = np.zeros(((total_cropped-discarded), height, width, 
                                  r_data.shape[3]), dtype=np.uint8)            
    
    cont = 0                                                              
    l_i = 0
    print("\n[CROP]: Collecting images . . .", flush=True)
    for img_num in tqdm(range(0, r_data.shape[0])): 
        for i in range(0, h_num):                                       
            for j in range(0, v_num):                     
                if discard == True and len(selected_images) != 0:
                    if selected_images[l_i] == cont \
                       or l_i == len(selected_images) - 1:

                        cropped_data[l_i]= r_data[img_num, 
                                                  (i*width):((i+1)*height), 
                                                  (j*width):((j+1)*height)]          

                        cropped_data_mask[l_i]= r_data_mask[img_num,                 
                                                            (i*width):((i+1)*height),
                                                            (j*width):((j+1)*height)]

                        if l_i != len(selected_images) - 1:
                            l_i = l_i + 1
                else: 
              
                    cropped_data[cont]= r_data[img_num, (i*width):((i+1)*height),      
                                               (j*width):((j+1)*height)]      
                                                                        
                    cropped_data_mask[cont]= r_data_mask[img_num,             
                                                         (i*width):((i+1)*height),
                                                         (j*width):((j+1)*height)]
                cont = cont + 1                                             
                                                                        
    if discard == True:
        print("\n" +str(discarded) + " images discarded. New shape after " 
              + "cropping and discarding is " + str(cropped_data.shape),
              flush=True)

    return cropped_data, cropped_data_mask, force_shape


def __mix_data(data, data_mask, num, out_shape=[1, 1], grid=True):
    """Combine images from input data into a bigger one given shape. It is the 
       opposite function of crop_data.

       Args:                                                                    
            data (4D numpy array): data to crop.                                
            data_mask (4D numpy array, optional): data masks to crop.
            num (int, optional): number of examples to convert.
            out_shape (int tuple, optional): number of horizontal and vertical
            images to combine in a single one.
            grid (bool, optional): make the grid in the output image.
                                                                                
       Returns:                                                                 
            mixed_data (4D numpy array): mixed data images.                 
            mixed_data_mask (4D numpy array): mixed data masks.
    """

    width = data.shape[1]
    height = data.shape[2] 
    total_mixed = out_shape[0]*out_shape[1]

    # Mix data
    mixed_data = np.zeros((total_mixed, out_shape[1]*width, 
                           out_shape[0]*height, 1), dtype=np.uint8)
    mixed_data_mask = np.zeros((total_mixed, out_shape[1]*width, 
                                out_shape[0]*height, 1), dtype=np.uint8)

    cont = 0
    for img_num in tqdm(range(0, mixed_data.shape[0])):
        for i in range(0, out_shape[1]):
            for j in range(0, out_shape[0]):

                if grid == True:
                    data[cont,0:data.shape[1]-1,0] = 255
                    data[cont,0:data.shape[1]-1,data.shape[2]-1] = 255
                    data[cont,0,0:data.shape[2]-1] = 255
                    data[cont,data.shape[1]-1,0:data.shape[2]-1] = 255
                    data_mask[cont,0:data_mask.shape[1]-1,0] = 1
                    data_mask[cont,0:data_mask.shape[1]-1,data_mask.shape[2]-1] = 1
                    data_mask[cont,0,0:data_mask.shape[2]-1] = 1
                    data_mask[cont,data_mask.shape[1]-1,0:data_mask.shape[2]-1] = 1
           
                mixed_data[img_num, (i*width):((i+1)*height), 
                           (j*width):((j+1)*height)] = data[cont]
    
                mixed_data_mask[img_num, (i*width):((i+1)*height),
                                (j*width):((j+1)*height)] = data_mask[cont]

                cont = cont + 1

    return mixed_data, mixed_data_mask


def check_crops(data, data_mask, out_dim, num_examples=2, out_dir="check_crops",
                job_id="none_job_id", grid=True):
    
    # First checks
    if out_dim[0] < data.shape[1] or out_dim[1] < data.shape[2]:
        print("\n[C_CROP] Aborting: out_dim must be equal or greater than" 
              + "data.shape", flush=True)
        return
    if data.shape != data_mask.shape:
        print("\n[C_CROP] Aborting: Data and data_mask has different shape.",
              flush=True)
        return
    out_dir = os.path.join(out_dir, job_id)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
   
    h_num = int(out_dim[0] / data.shape[1])
    v_num = int(out_dim[1] / data.shape[2])
    total = h_num*v_num
    
    if total*num_examples > data.shape[0]:
        num_examples = ceil(data.shape[0]/(total*num_examples))
        print("\n[C_CROP] Requested num_examples too high. Set automatically to" 
              + str(num_examples), flush=True)    

    print("\n[C_CROP] Saving cropped images . . .", flush=True)
    for i in tqdm(range(0, total)):
        for j in range(0, num_examples):
            im = Image.fromarray(data[(i*num_examples)+j,:,:,0])
            im = im.convert('L')
            im.save(os.path.join(out_dir,"c_" + "x" + str((i*num_examples)+j) + ".png"))
    
            im = Image.fromarray(data_mask[(i*num_examples)+j,:,:,0]*255)
            im = im.convert('L')
            im.save(os.path.join(out_dir,"c_" + "y" + str((i*num_examples)+j) + ".png"))

    print("\n[C_CROP] Mixing " + str(num_examples) + " images from ["
          + str(data.shape[1]) + "," + str(data.shape[2]) + "] to ["
          + str(data.shape[1]*h_num) + "," + str(data.shape[2]*v_num) + "]",
          flush=True)
    m_data, m_mask_data = __mix_data(data, data_mask, num_examples, 
                                     out_shape=[h_num, v_num], grid=True) 
   
    print("\n[C_CROP] Saving mixed images . . .", flush=True)
    for i in tqdm(range(0, num_examples)):    
        im = Image.fromarray(m_data[i,:,:,0])
        im = im.convert('L')
        im.save(os.path.join(out_dir,"f_x" + str(i) + ".png"))

        im = Image.fromarray(m_mask_data[i,:,:,0]*255)
        im = im.convert('L')
        im.save(os.path.join(out_dir,"f_y" + str(i) + ".png"))


def elastic_transform(image, alpha, sigma, alpha_affine, seed=None):
    """Elastic deformation of images as described in [Simard2003]_ (with i
       modifications).
       [Simard2003] Simard, Steinkraus and Platt, "Best Practices for 
       Convolutional Neural Networks applied to Visual Document Analysis", in
       Proc. of the International Conference on Document Analysis and
       Recognition, 2003.
       Based on:
           https://gist.github.com/erniejunior/601cdf56d2b424757de5
       Code obtained from:
           https://www.kaggle.com/bguberfain/elastic-transform-for-data-augmentation
    """
    if seed is None:
        random_state = np.random.RandomState(None)
    else:
        random_state = np.random.RandomState(seed)

    shape = image.shape
    shape_size = shape[:2]
    
    # Random affine
    center_square = np.float32(shape_size) // 2
    square_size = min(shape_size) // 3
    pts1 = np.float32([center_square + square_size, [center_square[0] 
                       + square_size, center_square[1]-square_size], 
                      center_square - square_size])
    pts2 = pts1 + random_state.uniform(-alpha_affine, alpha_affine, 
                                       size=pts1.shape).astype(np.float32)
    M = cv2.getAffineTransform(pts1, pts2)
    image = cv2.warpAffine(image, M, shape_size[::-1],
                           borderMode=cv2.BORDER_REFLECT_101)

    dx = gaussian_filter((random_state.rand(*shape) * 2 - 1), sigma) * alpha
    dy = gaussian_filter((random_state.rand(*shape) * 2 - 1), sigma) * alpha
    dz = np.zeros_like(dx)

    x, y, z = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]),         
                          np.arange(shape[2]))
    indices = np.reshape(y+dy, (-1, 1)), np.reshape(x+dx, (-1, 1)), \
                         np.reshape(z, (-1, 1))
    map_ = map_coordinates(image, indices, order=1, mode='reflect')
    map_ = map_.reshape(shape)
    return map_


class ImageDataGenerator(keras.utils.Sequence):
    """Custom ImageDataGenerator.
       Based on:
           https://github.com/czbiohub/microDL 
           https://stanford.edu/~shervine/blog/keras-how-to-generate-data-on-the-fly
    """

    def __init__(self, X, Y, batch_size=32, dim=(256,256), n_channels=1, 
                 shuffle=False, da=True, e_prob=0.9, elastic=False, vflip=False,
                 hflip=False, rotation=False):
        """ ImageDataGenerator constructor.
                                                                                
       Args:                                                                    
            X (numpy array): train data.                                  
            Y (numpy array): train mask data.                             
            batch_size (int, optional): size of the batches.
            dim (tuple, optional): dimension of the desired images.
            n_channels (int, optional): number of channels of the input images.
            shuffle (bool, optional): to decide if the indexes will be shuffled
            after every epoch. 
            da (bool, optional): to activate the data augmentation. 
            e_prob (float, optional): probability of making elastic
            transformations. 
            elastic (bool, optional): to make elastic transformations.
            vflip (bool, optional): if true vertical flip are made.
            hflip (bool, optional): if true horizontal flips are made.          
            rotation (bool, optional): to make rotations of 90º, 180º or 270º.
        """

        self.dim = dim
        self.batch_size = batch_size
        self.Y = Y
        self.X = X
        self.n_channels = n_channels
        self.shuffle = shuffle
        self.da = da
        self.e_prob = e_prob
        self.elastic = elastic
        self.vflip = vflip
        self.hflip = hflip
        self.rotation = rotation
        self.on_epoch_end()
        
        if self.X.shape[1] == self.X.shape[2]:
            self.squared = True
        else:
            self.squared = False
            if rotation == True:
                print("\n[AUG] Images not square, only 180 rotations will be" 
                      + " done.", flush=True)

        # Create a list which will hold a counter of the number of times a 
        # transformation is performed. 
        self.t_counter = [0 ,0 ,0 ,0 ,0 ,0] 

    def __len__(self):
        """Defines the number of batches per epoch."""
        return int(np.floor(len(self.X) / self.batch_size))

    def __getitem__(self, index):
        """Generation of one batch data. 
           Arg:
               index (int): batch index counter.
            
           Return:
               batch_x (numpy array): corresponding X elements of the batch.
               batch_y (numpy array): corresponding Y elements of the batch.
        """

        batch_x = np.empty((self.batch_size, *self.dim, self.n_channels))
        batch_y = np.empty((self.batch_size, *self.dim, self.n_channels))

        # Generate indexes of the batch
        indexes = self.indexes[index*self.batch_size:(index+1)*self.batch_size]
        
        for i, j in zip( range(0,self.batch_size), indexes ):
            if self.da == False: 
                 batch_x[i], batch_y[i] = self.X[j], self.Y[j]
            else:
                batch_x[i], batch_y[i], _ = self.apply_transform(self.X[j],
                                                              self.Y[j])
 
        return batch_x, batch_y

    def print_da_stats(self):
        """Print the counter of the transformations made in a table."""
        t = Texttable()
        t.add_rows([['Elastic', 'V. flip', 'H. flip', '90º rot.', '180º rot.',
                     '270º rot.'], [self.t_counter[0], self.t_counter[1],
                     self.t_counter[2], self.t_counter[3], self.t_counter[4], 
                     self.t_counter[5]] ])
        print(t.draw())

    def on_epoch_end(self):
        """Updates indexes after each epoch."""
        self.indexes = np.arange(len(self.X))
        if self.shuffle == True:
            np.random.shuffle(self.indexes)

    def __draw_grid(self, im, grid_width=50, m=False):
        """Draw grid of the specified size on an image. 
           
           Args:                                                                
               im (2D numpy array): image to be modified.
               grid_width (int, optional): grid's width. 
               m (bool, optional): advice the method to change the grid value
               if the input image is a mask.
        """

        if m == True:
            v = 1
        else:
            v = 255

        for i in range(0, im.shape[1], grid_width):
            im[:, i] = v
        for j in range(0, im.shape[0], grid_width):
            im[j, :] = v

    def apply_transform(self, image, mask, flow=False):
        """Transform the input image and its mask at the same time with one of
           the selected choices based on a probability. 
                
           Args:
               image (2D numpy array): image to be transformed.
               mask (2D numpy array): image's mask.
               flow (bool, optional): forces the transform independetly of the
               previously selected probability. Also draws a grid in to the 
               elastic transfomations to visualize it clearly. Do not set this 
               option to train the network!
        """
        trans_image = image
        trans_mask = mask
        transform_string = '' 
        transformed = False

        # Elastic transformation
        prob = random.uniform(0, 1)
        if (self.elastic == True or flow == True) and prob < self.e_prob:

            if flow == True:
                self.__draw_grid(trans_image)
                self.__draw_grid(trans_mask, m=True)

            im_concat = np.concatenate((trans_image, trans_mask), axis=2)            

            im_concat_r = elastic_transform(im_concat, im_concat.shape[1]*2,
                                            im_concat.shape[1]*0.08,
                                            im_concat.shape[1]*0.08)

            trans_image = np.expand_dims(im_concat_r[...,0], axis=-1)
            trans_mask = np.expand_dims(im_concat_r[...,1], axis=-1)
            transform_string = '_e'
            transformed = True
            self.t_counter[0] = self.t_counter[0] + 1
     
 
        # [0-0.25) : vertical flip
        # [0.25-0.5): horizontal flip
        # [0.5-0.75): vertical + horizontal flip
        # [0.75-1]: nothing
        #
        # Vertical flip
        prob = random.uniform(0, 1)
        if (self.vflip == True or flow == True) and 0 <= prob < 0.25:
            trans_image = np.flip(trans_image, 0)
            trans_mask = np.flip(trans_mask, 0)
            transform_string = transform_string + '_vf'
            transformed = True 
            self.t_counter[1] = self.t_counter[1] + 1
        # Horizontal flip
        elif (self.hflip == True or flow == True) and 0.25 <= prob < 0.5:
            trans_image = np.flip(trans_image, 1)
            trans_mask = np.flip(trans_mask, 1)
            transform_string = transform_string + '_hf'
            transformed = True
            self.t_counter[2] = self.t_counter[2] + 1 
        # Vertical and horizontal flip
        elif (self.hflip == True or flow == True) and 0.5 <= prob < 0.75:
            trans_image = np.flip(trans_image, 0)                               
            trans_mask = np.flip(trans_mask, 0)
            trans_image = np.flip(trans_image, 1)                               
            trans_mask = np.flip(trans_mask, 1)
            
        
        # [0-0.25) : 90º rotation
        # [0.25-0.5): 180º rotation
        # [0.5-0.75): 270º rotation
        # [0.75-1]: nothing
        # Note: if the images are not squared only 180 rotations will be done.
        prob = random.uniform(0, 1)
        if self.squared == True:
            # 90 degree rotation
            if (self.rotation == True or flow == True) and 0 <= prob < 0.25:
                trans_image = np.rot90(trans_image)
                trans_mask = np.rot90(trans_mask)
                transform_string = transform_string + '_r90'
                transformed = True 
                self.t_counter[3] = self.t_counter[3] + 1
            # 180 degree rotation
            elif (self.rotation == True or flow == True) and 0.25 <= prob < 0.5:
                trans_image = np.rot90(trans_image, 2)
                trans_mask = np.rot90(trans_mask, 2)
                transform_string = transform_string + '_r180'
                transformed = True 
                self.t_counter[4] = self.t_counter[4] + 1
            # 270 degree rotation
            elif (self.rotation == True or flow == True) and 0.5 <= prob < 0.75:
                trans_image = np.rot90(trans_image, 3)
                trans_mask = np.rot90(trans_mask, 3)
                transform_string = transform_string + '_r270'
                transformed = True 
                self.t_counter[5] = self.t_counter[5] + 1
        else:
            if (self.rotation == True or flow == True) and 0 <= prob < 0.5:
                trans_image = np.rot90(trans_image, 2)                          
                trans_mask = np.rot90(trans_mask, 2)                            
                transform_string = transform_string + '_r180'                   
                transformed = True                                              
                self.t_counter[4] = self.t_counter[4] + 1

        if transformed == False:
            transform_string = '_none'         

        return trans_image, trans_mask, transform_string


    def flow_on_examples(self, num_examples, job_id="none_job_id", out_dir='aug',
                         save_prefix=None, original_elastic=True,
                         random_images=True):
        """Apply selected transformations to a defined number of images from
           the dataset. The purpose of this method is to check the images 
           generated by data augmentation. 
            
           Args:
               num_examples (int): number of examples to generate.
               job_id (str, optional): job identifier. If any provided the
               examples will be generated under a folder called 'aug/none_job_id'.
               out_dir (str, optional): name of the folder where the 
               examples will be stored. If any provided the examples will be 
               generated under a folder called 'aug/none_job_id'.
               save_prefix (str, optional): prefix to add to the generated 
               examples' name. 
               original_elastic (bool, optional): to save also the original
               images when an elastic transformation is performed.
               random_images (bool, optional): randomly select images from the
               dataset. If False the examples will be generated from the start
               of the dataset. 
        """
        print("\n[FLOW] Creating the examples of data augmentation . . .", 
              flush=True)

        prefix = ""
        if 'save_prefix' in locals():
            prefix = str(save_prefix)

        out_dir = os.path.join(out_dir, job_id) 
        if not os.path.exists(out_dir):                              
            os.makedirs(out_dir)

        # Generate the examples 
        for i in tqdm(range(0,num_examples)):
            if random_images == True:
                pos = random.randint(1,self.X.shape[0]-1) 
            else:
                pos = cont 

            im = self.X[pos]
            mask = self.Y[pos]

            out_im, out_mask, t_str = self.apply_transform(im, mask, flow=True)

            out_im = Image.fromarray(out_im[:,:,0])                           
            out_im = out_im.convert('L')                                                    
            out_im.save(os.path.join(out_dir, prefix + 'x_' + str(pos) + t_str 
                                     + ".png"))          
                 
            out_mask = Image.fromarray(out_mask[:,:,0]*255)                           
            out_mask = out_mask.convert('L')                                                    
            out_mask.save(os.path.join(out_dir, prefix + 'y_' + str(pos) + t_str
                                       + ".png"))          
                
            # Save also the original images if an elastic transformation was made
            if original_elastic == True and '_e' in t_str: 
                im = Image.fromarray(im[:,:,0])
                im = im.convert('L')
                im.save(os.path.join(out_dir, prefix + 'x_' + str(pos) + t_str 
                                     + '_original.png'))

                mask = Image.fromarray(mask[:,:,0]*255)
                mask = mask.convert('L')
                mask.save(os.path.join(out_dir, prefix + 'y_' + str(pos) + t_str
                                       + '_original.png'))


def fixed_dregee(image):
    """Rotate given image with a fixed degree

       Args:
            image (img): image to be rotated.

       Returns:
            out_image (numpy array): image rotated.
    """
    img = np.array(image)

    # get image height, width
    (h, w) = img.shape[:2]
    # calculate the center of the image
    center = (w / 2, h / 2)

    M = cv2.getRotationMatrix2D(center, 180, 1.0)
    out_image = cv2.warpAffine(img, M, (w, h))
    out_image = np.expand_dims(out_image, axis=-1)
    return out_image


def keras_da_generator(X_train, Y_train, X_val, Y_val, batch_size_value, 
                       save_examples=True, job_id="none_job_id", out_dir='aug', 
                       hflip=True, vflip=True, seedValue=42, fill_mode='reflect',
                       preproc_function=True):

    """Makes data augmentation of the given input data.

       Args:
            X_train (numpy array): train data.
            Y_train (numpy array): train mask data.
            X_val (numpy array): validation data.
            Y_val (numpy array): validation mask data.
            batch_size_value (int): batch size.
            save_examples (bool, optional): if true 5 examples of DA are stored.
            job_id (str, optional): job identifier. If any provided the
            examples will be generated under a folder called 'aug/none_job_id'.
            out_dir (string, optional): save directory suffix.
            hflip (bool, optional): if true horizontal flips are made.
            vflip (bool, optional): if true vertical flip are made.
            seedValue (int, optional): seed value.
            fill_mode (str, optional): ImageDataGenerator of Keras fill mode 
            values.
            preproc_function (bool, optional): if true preprocess function to
            make random 180 degrees rotations are performed. 

       Returns:
            train_generator (Keras iterable of flow_from_directory): train data
            iterator.
            val_generator (Keras iterable of flow_from_directory): validation 
            data iterator.
    """
    
    if (preproc_function == True):
        data_gen_args = dict(horizontal_flip=hflip, vertical_flip=vflip,
                             fill_mode=fill_mode,
                             preprocessing_function=fixed_dregee)
    else:
        data_gen_args = dict(horizontal_flip=hflip, vertical_flip=vflip,
                             fill_mode=fill_mode, rotation_range=180)
                             
    
    # Train data, provide the same seed and keyword arguments to the fit and 
    # flow methods
    X_datagen_train = kerasDA(**data_gen_args)
    Y_datagen_train = kerasDA(**data_gen_args)
    X_datagen_train.fit(X_train, augment=True, seed=seedValue)
    Y_datagen_train.fit(Y_train, augment=True, seed=seedValue)
    
    # Validation data, no data augmentation, but we create a generator anyway
    X_datagen_val = kerasDA()
    Y_datagen_val = kerasDA()
    X_datagen_val.fit(X_val, augment=False, seed=seedValue)
    Y_datagen_val.fit(Y_val, augment=False, seed=seedValue)
    
    # Check a few of generated images
    if (save_examples == True):
        
        out_dir = os.path.join(out_dir, job_id)
        if not os.path.exists(out_dir):          
            os.makedirs(out_dir)
     
        i = 0
        for batch in X_datagen_train.flow(X_train, 
                                          save_to_dir=out_dir,
                                          batch_size=batch_size_value,
                                          shuffle=True, seed=seedValue,
                                          save_prefix='x', save_format='jpeg'):
            i = i + 1
            if i > 5:
                break
        i = 0
        for batch in Y_datagen_train.flow(Y_train, 
                                          save_to_dir=out_dir,
                                          batch_size=batch_size_value,
                                          shuffle=True, seed=seedValue,
                                          save_prefix='y', save_format='jpeg'):
            i = i + 1
            if i > 5:
                break
    
    X_train_augmented = X_datagen_train.flow(X_train, 
                                             batch_size=batch_size_value,
                                             shuffle=False, seed=seedValue)
    Y_train_augmented = Y_datagen_train.flow(Y_train, 
                                             batch_size=batch_size_value,
                                             shuffle=False, seed=seedValue)
    X_val_flow = X_datagen_val.flow(X_val, batch_size=batch_size_value,
                                    shuffle=False, seed=seedValue)
    Y_val_flow = Y_datagen_val.flow(Y_val, batch_size=batch_size_value,
                                    shuffle=False, seed=seedValue)
    
    # Combine generators into one which yields image and masks
    train_generator = zip(X_train_augmented, Y_train_augmented)
    val_generator = zip(X_val_flow, Y_val_flow)
    
    return train_generator, val_generator
