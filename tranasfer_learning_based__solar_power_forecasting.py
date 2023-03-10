# -*- coding: utf-8 -*-
"""Tranasfer_Learning_based _solar_power_forecasting.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1-C7vHqN1L2pW10SLBi0q7oEFFDjyhhVs
"""

from google.colab import drive
drive.mount('/content/drive')

import os
import random
import math
import numpy as np
from sklearn import preprocessing

import os
import pandas as pd
import zipfile

import pandas as pd
from datetime import datetime, timedelta
import numpy as np

from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.impute import KNNImputer

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split

class DataPreparation:
    
    def __init__(self, data_path):

        self.data_path = data_path
        self.df = None
        
    def unzip_files(self):

        # Unzip the files from the given path
        with zipfile.ZipFile(self.data_path, 'r') as zip_ref:
            zip_ref.extractall()
        
    def get_files_by_name(self, site_name):

        # Return the list of files with the given site name
        files = [f for f in os.listdir() if f.startswith(site_name) and f.endswith(".parquet")]
        return files
    
    def merge_files(self, files):

        # Read in each selected file as a dataframe and store in a list
        df_list = [pd.read_parquet(f).sort_values("datetime") for f in files]

        # Merge the dataframes into a single dataframe
        df_final = pd.DataFrame()
        df_final = df_list[0]
        for i in range(1, len(df_list)):
            df_final = df_final.merge(df_list[i], on="datetime", how="outer")
        for col in df_final.columns:
            if '_dcpowers_dcpu_' in col:
                df_final.drop([col],axis=1,inplace=True)
        df_final.drop(['pvexport_data_power_reactive','pvexport_data_voltage','pvexport_data_current','peripheral_data_relhumid','peripheral_data_dewpoint','pvexport_data_frequency'],axis=1,inplace=True)
        df_final.drop(columns=[col for col in df_final.columns if col.endswith("status")], inplace=True)
        self.df = df_final
        return df_final
    
    def resample_data(self, time_step):

        # Resample the data to the given time step
        self.df = self.df.resample(time_step).mean()
    
    def interpolate_missing(self):

        site_wind_angle=[f'site_peripheral_winds_station_{i}_angle' for i in range(1,7)]
        site_wind_speed=[f'site_peripheral_winds_station_{i}_speed' for i in range(1,7)]
        site_airtemp=[f'site_peripheral_airtemps_station_{i}' for i in range(1,7)]
        site_humidities=[f'site_peripheral_humidities_station_{i}' for i in range(1,7)]
        site_rainfalls=[f'site_peripheral_rainfalls_station_{i}' for i in range(1,7)]
        site_paneltemp=[f'site_peripheral_paneltemps_station_{i}' for i in range(1,7)]
        site_irradiance_hori=[f'site_peripheral_irradiances_station_{i}_hrzntl' for i in range(1,7)]
        site_irradiance_normal=[f'site_peripheral_irradiances_station_{i}_normal' for i in range(1,7)]
        cols=['peripheral_data_baropress','peripheral_data_airtemp','peripheral_data_windangle','peripheral_data_windspeed','peripheral_data_pyroup','peripheral_data_pyroangle']
        self.df[site_wind_angle+site_wind_speed+site_airtemp+site_humidities+site_rainfalls+site_paneltemp+cols+site_irradiance_hori+site_irradiance_normal]=self.df[site_wind_angle+site_wind_speed+site_airtemp+site_humidities+site_rainfalls+site_paneltemp+cols+site_irradiance_hori+site_irradiance_normal].interpolate(method='linear',limit_direction='both')
        imputer = KNNImputer(n_neighbors=5)
        pvexport_col = ['pvexport_data_power_real']
        self.df[pvexport_col] = imputer.fit_transform(self.df[pvexport_col])  

    def remove_outliers(self):

        percentile_dict={}
        outlier_imputer_dict = {}
        NinetyNine_percentile = np.percentile(self.df['pvexport_data_power_real'],99)  
        First_percentile = np.percentile(self.df["pvexport_data_power_real"],1)
        percentile_dict['99th'] =  NinetyNine_percentile
        percentile_dict['1st'] =  First_percentile  
        outlier_imputer_dict["pvexport_data_power_real"] = percentile_dict
        np.save('outlier_imputer_dict',outlier_imputer_dict) 
        outlier_dict = np.load('outlier_imputer_dict.npy',allow_pickle='TRUE').item()
        #Loading Outlier Imputer dictionary
        self.df.loc[self.df[self.df["pvexport_data_power_real"] > outlier_dict["pvexport_data_power_real"]['99th']].index,"pvexport_data_power_real"] = outlier_dict["pvexport_data_power_real"]['99th']  
        self.df.loc[self.df[self.df["pvexport_data_power_real"] < outlier_dict["pvexport_data_power_real"]['1st']].index,"pvexport_data_power_real"] = outlier_dict["pvexport_data_power_real"]['1st']

    def insert_block(self):

        self.df.reset_index(inplace=True)
        tb = pd.date_range('15-05-2020','16-05-2020',freq='15min')
        tb=tb[:-1] 
        ts = tb.strftime('%H:%M')
        block_dict = {}
        j=1
        for i in range(len(ts)):
            block_dict[ts[i]] =  j
            j+=1
        # Making new columns of Time,BLOCK and Date and droping DATE_TIME column
        self.df['TIME'] = self.df['datetime'].apply(lambda x:str(x)[-8:-3])
        self.df['DATE'] = pd.to_datetime(self.df['datetime']).dt.date
        self.df['BLOCK'] = pd.to_datetime(self.df['TIME']).astype(str).apply(lambda x:block_dict[str(x)[-8:-3]])
        self.df.drop('datetime',axis=1,inplace=True)
        cols = self.df.columns.tolist()
        self.df = self.df[[cols[-1]]+[cols[-2]]+[cols[-3]]+cols[:-3]]

    def negative_zero(self):

        self.df['pvexport_data_power_real'] = self.df['pvexport_data_power_real'].apply(lambda x: 0 if x < 0 else x)

    def prepare_data(self, site_name, time_step):
         # unzip files
        self.unzip_files()
        # Get the list of files for the given site name

        files = self.get_files_by_name(site_name)
        # Merge the files into a single dataframe

        self.merge_files(files)
        # Interpolate missing values

        self.interpolate_missing()
        # outliers handling

        self.remove_outliers()
        # Resample the data to the given time step

        self.resample_data(time_step)
        # block

        self.insert_block()
        # Negative values

        self.negative_zero()

        return self.df

class DataPreprocessor():
    def __init__(self,data,train_size=0.8,shuffle=True,test_size=0.2):
        self.df=data

        self.y=self.df['pvexport_data_power_real']
        self.X=self.df.drop(["pvexport_data_power_real"],axis=1)

        self.shuffle=shuffle

        self.train_size=train_size
        self.test_size=test_size

        self.X_train=None
        self.y_train=None

        self.X_val =None
        self.y_val =None

        self.X_test =None
        self.y_test =None

        self.X_train_scaled=None
 

        self.X_val_scaled =None


        self.X_test_scaled =None

    def split_data(self):
        if (self.shuffle):

            self.X['Target']=self.y
            self.X['DATE'] = pd.to_datetime(self.X['DATE'])
            test_data = self.X[(self.X['DATE'] >= '2020-11-01') & (self.X['DATE'] <= '2020-12-07')]

            # Filter the remaining data to eself.Xclude the test data
            train_val_data = self.X[~self.X.isin(test_data)].dropna()

            # Split the remaining data into training and validation data
            train_data, val_data = train_test_split(train_val_data, test_size=self.test_size, shuffle=self.shuffle, random_state=42)

            self.X_train=train_data.drop(['BLOCK','DATE','TIME','Target'],axis=1)
            self.y_train=train_data['Target']

            self.X_val=val_data.drop(['BLOCK','DATE','TIME','Target'],axis=1)
            self.y_val=val_data['Target']

            self.X_test=test_data.drop(['BLOCK','DATE','TIME','Target'],axis=1)
            self.y_test=test_data['Target']

        else:
            self.X['Target']=self.y

            self.X['DATE'] = pd.to_datetime(self.X['DATE'])
            test_data = self.X[(self.X['DATE'] >= '2020-11-01') & (self.X['DATE'] <= '2020-12-07')]

            # Filter the remaining data to eself.Xclude the test data
            train_val_data = self.X[~self.X.isin(test_data)].dropna()

            # Split the remaining data into training and validation data
            train_data, val_data = train_test_split(train_val_data, test_size=self.test_size, shuffle=self.shuffle, random_state=42)

            self.X_train=train_data.drop(['BLOCK','DATE','TIME','Target'],axis=1)
            self.y_train=train_data['Target']

            self.X_val=val_data.drop(['BLOCK','DATE','TIME','Target'],axis=1)
            self.y_val=val_data['Target']

            self.X_test=test_data.drop(['BLOCK','DATE','TIME','Target'],axis=1)
            self.y_test=test_data['Target']

    def scale_data(self):
        scaler = MinMaxScaler()
        # Fit the scaler to the training data
        scaler.fit(self.X_train)

        # Transform the training, validation, and test data
        self.X_train_scaled = scaler.transform(self.X_train)
        self.X_val_scaled = scaler.transform(self.X_val)
        self.X_test_scaled = scaler.transform(self.X_test)
        return (self.X,self.y,self.X_train_scaled,self.X_val_scaled,self.X_test_scaled,self.y_train,self.y_val,self.y_test)

dp=DataPreparation('/content/drive/MyDrive/ARENA/public_dataset.zip')
df_final=dp.prepare_data('DDSF1','15T')

prep=DataPreprocessor(df_final,shuffle=False)
prep.split_data()
X,Y,X_train,X_val,X_test,y_train,y_val,y_test=prep.scale_data()

from sklearn.preprocessing import RobustScaler, StandardScaler, MinMaxScaler, MaxAbsScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.sequence import TimeseriesGenerator

class DataScaler:
    
    def __init__(self, scaling_strategy):
        self.scaling_strategy = scaling_strategy
    
    def scale_data(self, scaling_data, scaling_columns):
        if self.scaling_strategy == "RobustScaler":
            scaler = RobustScaler()
        elif self.scaling_strategy == "StandardScaler":
            scaler = StandardScaler()
        elif self.scaling_strategy == "MinMaxScaler":
            scaler = MinMaxScaler()
        elif self.scaling_strategy == "MaxAbsScaler":
            scaler = MaxAbsScaler()
        else:
            scaler = RobustScaler()  # If any other scaling is sent by mistake, still perform Robust Scalar
        scaling_data[scaling_columns] = scaler.fit_transform(scaling_data[scaling_columns])
        return scaling_data
    
    def split_data(self, X, y):
        X_train, X_val, y_train, y_val = train_test_split(X, y, train_size=0.7, random_state=42, shuffle=False)
        X_val, X_test, y_val, y_test = train_test_split(X_val, y_val, test_size=0.5, random_state=8, shuffle=False)
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def generate_time_series(self, features, target):
        # multi_target = pd.concat([target['Ghi'].shift(-i) for i in range(13)], axis=1).iloc[:, -1].dropna().to_numpy().tolist()
        multi_target=pd.concat([target.shift(-i) for i in range(13)],axis=1).iloc[:,-1].dropna().to_numpy().tolist()
        generator = TimeseriesGenerator(features[:-12], multi_target, length=12, sampling_rate=1, batch_size=128, stride=1)
        return generator
    
    def preprocess_data(self, X, y, validation_data=None):
        X_train, X_val, X_test, y_train, y_val, y_test = self.split_data(X, y)
        
        X_train = self.scale_data(X_train.drop(['BLOCK','DATE','TIME'],axis=1),X_train.drop(['BLOCK','DATE','TIME'],axis=1).columns)
        X_val = self.scale_data(X_val.drop(['BLOCK','DATE','TIME'],axis=1), X_val.drop(['BLOCK','DATE','TIME'],axis=1).columns)
        X_test = self.scale_data(X_test.drop(['BLOCK','DATE','TIME'],axis=1), X_test.drop(['BLOCK','DATE','TIME'],axis=1).columns)
        
        train_generator = self.generate_time_series(X_train.to_numpy().tolist(), y_train)
        val_generator = self.generate_time_series(X_val.to_numpy().tolist(), y_val)
        test_generator = self.generate_time_series(X_test.to_numpy().tolist(), y_test)
        return train_generator, val_generator, test_generator

Ds=DataScaler("MinMaxScaler")
train_generator, val_generator, test_generator=Ds.preprocess_data(X,Y)

import tensorflow as tf
from tensorflow.keras.layers import LSTM, Dense, Bidirectional, Input, Concatenate, Dropout
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

class SolarPowerForecastingModel:

    def __init__(self, n_timesteps, n_features, n_outputs):
        self.n_timesteps = n_timesteps
        self.n_features = n_features
        self.n_outputs = n_outputs
        self.model = None

    def build_model(self):
        inputs = Input(shape=(self.n_timesteps, self.n_features))
        x = LSTM(256, return_sequences=True)(inputs)
        x = Dropout(0.2)(x)
        x = LSTM(256,return_sequences=True)(x)
        x = Dropout(0.2)(x)
        outputs = Dense(self.n_outputs, activation ='linear')(x)
        self.model = Model(inputs=inputs, outputs=outputs)

    def train_model(self,train_generator, val_generator, epochs, batch_size):
        es = EarlyStopping(monitor='val_loss', patience=10, verbose=1)
        mc = ModelCheckpoint('best_model.h5', monitor='val_loss', mode='min', verbose=1, save_best_only=True)
        self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        self.model.fit(train_generator, epochs=epochs, batch_size=batch_size, validation_data=val_generator, callbacks=[es, mc])

    def load_trained_model(self, path):
        self.model = load_model(path)

    def save_trained_model(self, path):
        self.model.save(path)
    def predict(self, X):
        return self.model.predict(X)

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
class SolarPowerForecastingModel:

    def __init__(self, n_timesteps, n_features, n_outputs):
        self.n_timesteps = n_timesteps
        self.n_features = n_features
        self.n_outputs = n_outputs
        self.model = None

    def build_model(self):
        self.model = Sequential()
        self.model.add(LSTM(24,return_sequences=True, input_shape=(self.n_timesteps, self.n_features)))
        self.model.add(LSTM(48,return_sequences=True))
        self.model.add(LSTM(96))
        self.model.add(Dense(self.n_outputs))
        self.model.compile(loss='mean_squared_error', optimizer=Adam(learning_rate=0.001), metrics=['mae'])

    def train_model(self,train_generator, val_generator, epochs, batch_size):
        # es = EarlyStopping(monitor='val_loss', patience=10, verbose=1)
        mc = ModelCheckpoint('best_model.h5', monitor='val_loss', mode='min', verbose=1, save_best_only=True)
        self.model.fit(train_generator, epochs=epochs, batch_size=batch_size, validation_data=val_generator, callbacks=[ mc])

    def load_trained_model(self, path):
        self.model = load_model(path)

    def save_trained_model(self, path):
        self.model.save(path)
    
    def predict(self, X):
        return self.model.predict(X)

sf=SolarPowerForecastingModel(12,56,1)
sf.build_model()
sf.train_model(train_generator,val_generator,2500,128)

sf.save_trained_model('/content/drive/MyDrive/Transfer_Learning')
sf.predict(train_generator)

from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Input, Dense, Dropout, Concatenate, Bidirectional, LSTM
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
import matplotlib.pyplot as plt
import numpy as np


class TransferLearningModel:

    def __init__(self, base_model_path, target_regions, n_timesteps, n_features, n_outputs):
        self.base_model_path = base_model_path
        self.target_regions = target_regions
        self.n_timesteps = n_timesteps
        self.n_features = n_features
        self.n_outputs = n_outputs
        self.model = None
        self.history = None

    def build_model(self):
        # Load the pre-trained model
        pre_trained_model = load_model(self.base_model_path)

        # Freeze all layers except the last LSTM layer
        for layer in pre_trained_model.layers[:-2]:
            layer.trainable = False

        # Get the last LSTM layer and add a new output layer for the target regions
        lstm_layer = pre_trained_model.layers[-2]
        target_outputs = []
        for _ in self.target_regions:
            region_output = Dense(self.n_outputs, activation='linear')(lstm_layer.output)
            target_outputs.append(region_output)

        # Concatenate the new output layers
        new_outputs = Concatenate()(target_outputs)

        # Create the new model with the frozen pre-trained layers and the new output layer
        self.model = Model(inputs=pre_trained_model.inputs, outputs=new_outputs)

    def train_model(self,train_generator, val_generator, epochs, batch_size):
        es = EarlyStopping(monitor='val_loss', patience=10, verbose=1)
        mc = ModelCheckpoint('best_model.h5', monitor='val_loss', mode='min', verbose=1, save_best_only=True)
        self.model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        self.history = self.model.fit(train_generator, epochs=epochs, batch_size=batch_size, validation_data=val_generator, callbacks=[es, mc])

    def save_trained_model(self, path):
        self.model.save(path)

    def load_trained_model(self, path):
        self.model = load_model(path)

    def evaluate(self, X_test, y_test):
        y_pred = self.model.predict(X_test)
        mse = np.mean(np.square(y_test - y_pred))
        mae = np.mean(np.abs(y_test - y_pred))
        rmse = np.sqrt(mse)
        print('MSE: {:.2f}, MAE: {:.2f}, RMSE: {:.2f}'.format(mse, mae, rmse))

        # Plot the error distribution
        errors = y_test - y_pred
        plt.hist(errors, bins=30)
        plt.xlabel('Error')
        plt.ylabel('Frequency')
        plt.title('Error Distribution')
        plt.show()

    def predict(self, X):
        return self.model.predict(X)

    def visualize_training(self):
        # Plot training & validation loss values
        plt.plot(self.history.history['loss'])
        plt.plot(self.history.history['val_loss'])
        plt.title('Model loss')
        plt.ylabel('Loss')
        plt.xlabel('Epoch')
        plt.legend(['Train', 'Validation'], loc='upper right')
        plt.show()

Tr_Bi_LSTM=TransferLearningModel('/content/drive/MyDrive/Transfer_Learning',['DAYDSF1'],12,56,1)
Tr_Bi_LSTM.build_model()

dp=DataPreparation('/content/drive/MyDrive/ARENA/public_dataset.zip')
df_final=dp.prepare_data('DAYDSF1','15T')
prep=DataPreprocessor(df_final,shuffle=False)
prep.split_data()
X,Y,X_train,X_val,X_test,y_train,y_val,y_test=prep.scale_data()
Ds=DataScaler("MinMaxScaler")
train_generator, val_generator, test_generator=Ds.preprocess_data(X,Y)

Tr_Bi_LSTM.train_model(train_generator,val_generator,epochs=2500,batch_size=128)
Tr_Bi_LSTM.visualize_training()

Tr_Bi_LSTM.predict(train_generator).tolist()

"""
 1. DDSF1
 2. DAYDSF1
 3. EMERASF1
 4. GANNSF1
 5. MANSLR1 



"""