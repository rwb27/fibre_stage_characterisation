
#import libraries
import cv2
import numpy as np
from scipy import ndimage, signal
import io
import sys
import time
from camera_stuff import get_numpy_image, find_template
import microscope
import picamera
import data_file
from openflexure_stage import OpenFlexureStage
import threading
import matplotlib.pyplot as plt
import matplotlib
import data_file
import h5py
import tweepy
import twitter_keys

if __name__ == "__main__":

    with picamera.PiCamera(resolution=(640,480)) as camera, OpenFlexureStage('/dev/ttyUSB0') as stage:
        
        #authorises the program to acces the twitter account
        auth = tweepy.OAuthHandler(twitter_keys.consumer_key, twitter_keys.consumer_secret)
        auth.set_access_token(twitter_keys.access_token,twitter_keys.access_token_secret)
        api = tweepy.API(auth)
        
        N_frames = 100
        counter = 0

        #loads camera from picamera and set the stage as the arduino, lower resolution can speed up the programme
        ms = microscope.Microscope(camera, stage)
        ms.freeze_camera_settings()
        frame = get_numpy_image(camera, True)

        df = data_file.Datafile(filename="drift_81217.hdf5") #creates the .hdf5 file to save the data
        data_gr = df.new_group("test_data", "A file of data collected to test this code works")
        #puts the data file into a group with description

        image = get_numpy_image(camera, greyscale=True) #takes template photo
        templ8 = image[100:-100,100:-100] #crops image

        loop = True
        tweet = True

        start_t = time.time() #measure starting time


        try:
            while loop:
                data = np.zeros((3, N_frames)) #creates the array in which data is stored
                for i in range(data.shape[1]):
                #takes 100 images and compares the location of the spot with the template
                    frame = get_numpy_image(camera, True)
                    spot_coord = find_template(templ8, frame)
                    data[1, i] = spot_coord[0]
                    data[2, i] = spot_coord[1]
                    data[0, i] = time.time() - start_t
                df.add_data(data, data_gr, "data") #writes data to .hdf5 file
                imgfile_location = "/home/pi/dev/fibre_stage_characterisation/frames/drift_%s.jpg" % time.strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(imgfile_location, frame)
                try:
                    if time.gmtime(time.time())[3] in [0, 4, 8, 12, 16, 20] and tweet: #tweets a picture and co-ordinates every 4 hours
                        api.update_with_media(imgfile_location, status="I'm currently at %d, %d" %(spot_coord[0], spot_coord[1]))
                        tweet = False
                    elif time.gmtime(time.time())[3] not in [0, 4, 8, 12, 16, 20]:
                        tweet = True
                except:
                    pass
        except KeyboardInterrupt:
            print "Got a keyboard interrupt, stopping"
            