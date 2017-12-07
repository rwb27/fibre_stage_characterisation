
from openflexure_stage import OpenFlexureStage
import numpy as np
import math
import time
import h5py
import data_file

def take_data(stage, points, samples, step_size, axis):
    data = np.zeros((points, 5))
    averages = np.zeros((samples, 1))
    stage.move_rel(np.dot(-(step_size * math.trunc(points / 2)), axis))
    for i in range(points):
        stage.move_rel(np.dot(step_size, axis))
        for j in range(samples):
            averages[j, 0] = stage.light_sensor_fullspectrum
            time.sleep(0.1)
        data[i, 0] = np.mean(averages, axis = 0)
        data[i, 1] = stage.light_sensor_gain
        data[i, 2:] = stage.position
    return data

if __name__ == "__main__":
    with OpenFlexureStage("/dev/ttyUSB0") as stage:

        gain = [1, 25, 428, 9876]
        stage.light_sensor_gain = 9876
        step_size = 500
        min_step = 50
        points = 5
        samples = 5
        j = 1

        stage.backlash = 256

        df = data_file.Datafile(filename = "hillwalk.hdf5")
        data_intensity = df.new_group("intensity reading over time", "hill walk")
        raw_data = df.new_group("data taken by take_data function", "hill walk")

        intensity_data = np.zeros((100, 5))

        start_time = time.time()

        intensity_data[0, 0] = start_time
        intensity_data[0, 1] = stage.light_sensor_fullspectrum
        intensity_data[0, 2:] = stage.position
        df.add_data(intensity_data, data_intensity, "intensity reading")

        while step_size > min_step:
            for axis in [[1, 0, 0], [0, 1, 0], [0, 0, 10]]:
                while True:
                    data = take_data(stage, points, samples, step_size, axis)
                    print data
                    df.add_data(data, raw_data, "data taken by take_data function")
                    if np.all(data[:, 0] < 10) == True:
                        current_gain = stage.light_sensor_gain
                        if current_gain < np.max(gain):
                            stage.light_sensor_gain = np.min([g for g in gain if g > current_gain])
                            continue
                    elif np.all(data[:, 0] > 2**15) == True:
                        current_gain = stage.light_sensor_gain
                        if current_gain > np.min(gain):
                            stage.light_sensor_gain = np.max([g for g in gain if g < current_gain])
                            continue
                    coefficients = np.polyfit(np.dot(data[:, 2:], axis), data[:, 0], 2)
                    if 2 * coefficients[0] > 0:
                        coefficient = np.polyfit(np.dot(data[:, 2:], axis), data[:, 0], 1)
                        if coefficient[0] > 0:
                            print "straight line with positive gradient"
                            stage.move_abs(data[points-1, 2:])
                            continue
                        elif coefficient[0] < 0:
                            print "straight line with negative gradient"
                            stage.move_abs(data[0, 2:])
                            continue
                    elif 2 * coefficients[0] < 0:
                        gradients = np.zeros((points, 1))
                        gradients[:, 0] = (2 * coefficients[0] * np.dot(data[:, 2:], axis)) + coefficients[1]
                        signs_sum = np.sum(np.sign(gradients[:, 0]))
                        if signs_sum == points:
                            print "Not at the peak yet, working hard on it"
                            stage.move_abs(data[points-1, 2:])
                            continue
                        elif signs_sum == -points:
                            print "Getting bored? I'm nearly there"
                            stage.move_abs(data[0, 2:])
                            continue
                        else:
                            print "Look I just found the peak"
                            pos_to_be = -(coefficients[1] / (2 * coefficients[0]))
                            stage.move_rel(np.dot((pos_to_be - np.dot(data[points-1, 2:], axis)), axis)/np.sum(np.array(axis)**2))
                            intensity_data[j, 0] = time.time() - start_time
                            intensity_data[j, 1] = stage.light_sensor_fullspectrum
                            intensity_data[j, 2:] = stage.position
                            j = j + 1
                            break
                
            step_size = np.rint(step_size / 2)
            print "Step size reduced to %d" %step_size
            
        df.add_data(intensity_data, data_intensity, "intensity reading over time")
            
        print stage.light_sensor_fullspectrum
        print stage.light_sensor_gain
        print stage.position
        