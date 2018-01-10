
# coding: utf-8

# ## Importing basic libraries

# In[868]:


#Setup
# get_ipython().magic('matplotlib inline')
# get_ipython().magic('config IPCompleter.greedy=True')
import datetime as dt
import pytz
import time
import os
import psycopg2
import numpy as np
import pandas as pd
import scipy
import matplotlib.pyplot as plt
from pythonLib.helper import *
import sqlalchemy
import backtrader.plot as pLaut

from keras.models import Sequential
from keras.layers import Activation,Dense,LSTM, Dropout,Conv1D,MaxPooling1D,Permute,Merge
from keras.layers import Flatten,BatchNormalization,LeakyReLU,GlobalAveragePooling1D
from keras.wrappers.scikit_learn import KerasClassifier
from keras.utils import np_utils
from keras.losses import binary_crossentropy
from keras.optimizers import SGD,Adam
from keras.models import load_model

import h5py

from sklearn.utils import class_weight
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import KFold
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import sklearn.preprocessing as skp
import tensorflow as tf
import tempfile
tf.__version__

# fix random seed for reproducibility
# seed = 7
DATA_DIR = 'data' 
# np.random.seed(seed)
dbString = 'postgresql://s2c:JANver95@localhost:5432/stockdata'
engine = sqlalchemy.create_engine(dbString) 
utc = pytz.UTC
starDate = utc.localize(dt.datetime(2016,1,2))
portVals = []

curIter = 0

while curIter==0 or startDate.year == 2016:
	query = "SELECT * FROM histdata WHERE ticker = 'HFCL' ORDER BY datetime ASC"
	dat = pd.read_sql(query,engine)


	startDate = starDate + dt.timedelta(days=7*curIter)
	endDate = startDate +dt.timedelta(days = 7*12) # 3months of training
	backTestStart = endDate
	backTestEnd = endDate + dt.timedelta(days=5)
	res = dat[(dat['datetime'] > startDate) & (dat['datetime'] < endDate)]
	curIter += 1

	# res


	# ## Some Helper Functions
	# 
	# These functions are more or less general functions that should prove to be fairly useful
	# 
	# 
	# - **ReadData(filename)** : Reads data from Zerodha API historical data files and returns a Pandas DataFrame
	# - **sycTimeSeries(ts1,ts2)** : Making sure that 2 timeseries are synced to the smaller time series
	# - **timeseriesLagged(data, lag=60)**: Creates Lagged series.Goes through a series and generates an lag+1  dimensional   pandas DataFrame that has each previous lag timeunit.
	# - **binarizeTime(resLagged, rate=0.01)** : Binarizes the last column into 1,-1 or 0 depending whether the price increased, decreased or stayed the same from the beginning to the end of the lag period (triggers on changes by magnitutde = rate*current price).
	# - **findLag(data, targetCorr,suppressed)** :  Finds the right lag given a target correlation.

	# ## Reading some Data and Getting a feel 
	# 
	# We use an autocorrelation plot to help us figure out what is an optimal amount of lag. We are really looking for a lag that correlates highly. We go through the lags till we reach the last lag that guarantees 0.97 autocorrelation
	# 
	# ## THIS DID NOT WORK AS EXPECTED. REPLACE WITH FALSE NEAREST NEIGHBOUR

	# In[925]:


	# # Setup Parameters
	dataInit = res # Read the stock price data. This is 1 minute data
	data = dataInit['close'] # extract the 'close' column as a Pandas series
	# plt.figure()
	# pd.tools.plotting.lag_plot(data) # Lag plot to check randomness
	# plt.figure()
	# pd.tools.plotting.autocorrelation_plot(data) # Auto correlation plot to check if series is autocorrelated at all

	# # Find the right lag manually
	# targetCorr = 0.99 # autocorrelation we want
	# lag = findLag(data,targetCorr,True) # Lag that is indicative 
	# if lag == 99: #if lag is 99 then we can just use any number above it as autocorrelation is guaranteed.
	#     lag = 120 #nice round 2  hour intervals
	# print(lag)
	lag = 30
	series = timeseriesLagged(data,lag) # Generate the lagged series


	# In[926]:


	# Create binary series where 0 = hold and 1 = buy
	buySeries = binarizeTime(series,0,)
	change = buySeries.iloc[:,-1]== -1 # convert to binary
	buySeries.loc[change,str(lag+1)]=0 # convert to binary


	# In[927]:


	# Create binary series where 0 = hold and 1 = sell
	sellSeries = binarizeTime(series,0)
	change = sellSeries.iloc[:,-1]== 1 # find 1s and convert to 0
	sellSeries.loc[change,str(lag+1)]=0 # 
	change = sellSeries.iloc[:,-1]== -1 # find -1 and conver to 1s
	sellSeries.loc[change,str(lag+1)]= 1 # convert to


	# # Generate Training Data
	# 
	# Now that we have an idea of what's going on in the dataset, it is a good time to generate training data. We do an 90:20 training:testing split, and then we randomize the training set because we assume that only the last LAG minutes matter

	# In[928]:



	# In[929]:


	# Get values from pandas series as we need a numpy array for our classifier
	BuySeriesVals = buySeries.values
	np.random.shuffle(BuySeriesVals) #shuffle the entire dataset
	trainPercent = 0.9 # first 80% of the data is used for training
	np.random.shuffle(BuySeriesVals)
	#Split into train and test
	trainBegin = int(trainPercent*len(BuySeriesVals)) 
	trains = BuySeriesVals[0:trainBegin]
	train,val = train_test_split(trains)
	test = BuySeriesVals[trainBegin:]
	# np.random.shuffle(train) # shuffle the training dataset

	# Split into x and y
	xTrain,yTrain = train[:,0:-1],train[:,-1] # X is the first lag elements. Y is the lag+1 element
	xVal,yVal = val[:,0:-1],val[:,-1] # Same for Validation
	xTest,yTest = test[:,0:-1],test[:,-1] # Same for testing data

	#scale function to local normalize each row between 0 and 1 so as to amplify any changes
	# standardize = lambda row: skp.normalize(row)
	xTrain =skp.scale(xTrain,axis=1) #np.apply_along_axis(standardize,1,xTrain) #scale to 01
	xTest = skp.scale(xTest,axis=1) #scale to 0 1
	xVal = skp.scale(xVal,axis=1) #scale to 0 1

	#Reshape for keras
	xTrain = xTrain.reshape(xTrain.shape[0], xTrain.shape[1],1)
	xTest = xTest.reshape(xTest.shape[0], xTest.shape[1],1)
	xVal = xVal.reshape(xVal.shape[0],xVal.shape[1],1)


	# # # encode class values as integers
	# encoder = LabelEncoder()
	# encoder.fit(yTrain)
	# encodedyTrain = encoder.transform(yTrain)
	# encodedyTest = encoder.transform(yTest)
	# encodedyVal = encoder.transform(yVal)
	# # convert integers to one hot encoded
	# yTrain = np_utils.to_categorical(encodedyTrain)
	# yTest = np_utils.to_categorical(encodedyTest)
	# yVal = np_utils.to_categorical(encodedyVal)




	# In[930]:


	# Compute Class weights
	classWeight = class_weight.compute_class_weight('balanced', np.unique(yTrain), yTrain)
	classWeight = dict(enumerate(classWeight))
	classWeight


	# In[931]:


	assert xTrain.shape[0] == yTrain.shape[0]
	assert xTest.shape[0] == yTest.shape[0]
	assert xVal.shape[0] == yVal.shape[0]
	xTrain.shape


	# # ConvNet for Buy
	# 
	# A CNN to predict buy signals from the above generated data

	# In[932]:


	learnRate = 0.5
	batchSize = 10
	totalBatches = (xTrain.shape[0]//batchSize)
	epochs = 5

	nClasses = 2
	nLength = xTrain.shape[1]
	inputShape = (nLength,1)
	# xTrainDataSet = tf.data.Dataset.from_tensors(xTrain)
	# xTrainIter = xTrainDataSet.make_one_shot_iterator()


	# In[933]:


	# Keras
	#https://arxiv.org/pdf/1709.05206.pdf LSTM-FCN
	buyModelConv = Sequential()
	buyModelConv.add(Conv1D(12,kernel_size= 1, strides=1,
	                 input_shape=inputShape,
	                 batch_size = None
	                   ))
	buyModelConv.add(BatchNormalization())
	buyModelConv.add(Activation('relu'))


	buyModelConv.add(Conv1D(6, kernel_size= 1, strides=1))
	buyModelConv.add(BatchNormalization())
	buyModelConv.add(Activation('relu'))

	buyModelConv.add(Conv1D(6,kernel_size= 1, strides=1))
	buyModelConv.add(BatchNormalization())
	buyModelConv.add(Activation('relu'))

	buyModelConv.add(GlobalAveragePooling1D())
	 ########################################
	buyModelLSTM = Sequential()
	buyModelLSTM.add(Permute((2, 1), input_shape=inputShape))
	buyModelLSTM.add(LSTM(5))
	buyModelLSTM.add(Dropout(0.5))
	#############################

	buyModel = Sequential()
	buyModel.add(Merge([buyModelConv, buyModelLSTM],mode='concat'))
	buyModel.add(Dense(1,activation='sigmoid'))


	# In[934]:


	# buyModel.summary()
	buyModel.compile(loss=binary_crossentropy,
	              optimizer=SGD(lr=learnRate),
	              metrics=['accuracy'])


	# In[935]:


	buyModel.fit(x=[xTrain,xTrain],
	             y=yTrain, 
	             class_weight=classWeight,
	             validation_data = ([xVal,xVal],yVal),
	             epochs = 5,
	             verbose = 0)


	# In[936]:


	score = buyModel.evaluate([xTest,xTest], yTest, verbose=0)
	print('Test loss:', score[0])
	print('Test accuracy:', score[1])


	# ## ConvNet for Sell

	# In[937]:


	# Get values from pandas series as we need a numpy array for our classifier
	sellSeriesVals = sellSeries.values
	trainPercent = 0.9 # first 80% of the data is used for training

	#Split into train and test
	trainBegin = int(trainPercent*len(sellSeriesVals)) 
	trains = sellSeriesVals[0:trainBegin]
	train,val = train_test_split(trains)
	test = sellSeriesVals[trainBegin:]
	np.random.shuffle(train) # shuffle the training dataset

	# Split into x and y
	xTrain,yTrain = train[:,0:-1],train[:,-1] # X is the first lag elements. Y is the lag+1 element
	xVal,yVal = val[:,0:-1],val[:,-1] # Same for Validation
	xTest,yTest = test[:,0:-1],test[:,-1] # Same for testing data

	#scale function to local normalize each row between 0 and 1 so as to amplify any changes
	# standardize = lambda row: skp.normalize(row)
	xTrain =skp.scale(xTrain,axis=1) #np.apply_along_axis(standardize,1,xTrain) #scale to 01
	xTest = skp.scale(xTest,axis=1) #scale to 0 1
	xVal = skp.scale(xVal,axis=1) #scale to 0 1

	#Reshape for keras
	xTrain = xTrain.reshape(xTrain.shape[0], xTrain.shape[1],1)
	xTest = xTest.reshape(xTest.shape[0], xTest.shape[1],1)
	xVal = xVal.reshape(xVal.shape[0],xVal.shape[1],1)



	# # # encode class values as integers
	# encoder = LabelEncoder()
	# encoder.fit(yTrain)
	# encodedyTrain = encoder.transform(yTrain)
	# encodedyTest = encoder.transform(yTest)
	# encodedyVal = encoder.transform(yVal)
	# # convert integers to one hot encoded
	# yTrain = np_utils.to_categorical(encodedyTrain)
	# yTest = np_utils.to_categorical(encodedyTest)
	# yVal = np_utils.to_categorical(encodedyVal)




	# In[938]:


	# Compute Class weights
	classWeight = class_weight.compute_class_weight('balanced', np.unique(yTrain), yTrain)
	classWeight = dict(enumerate(classWeight))
	xTest.shape
	assert xTrain.shape[0] == yTrain.shape[0]
	assert xTest.shape[0] == yTest.shape[0]
	assert xVal.shape[0] == yVal.shape[0]
	yTrain
	learnRate = 0.5
	batchSize = 10
	totalBatches = (xTrain.shape[0]//batchSize)
	epochs = 5

	nClasses = 2
	nLength = xTrain.shape[1]
	inputShape = (nLength,1)
	# xTrainDataSet = tf.data.Dataset.from_tensors(xTrain)
	# xTrainIter = xTrainDataSet.make_one_shot_iterator()


	# In[939]:


	# Keras
	#https://arxiv.org/pdf/1709.05206.pdf LSTM-FCN
	sellModelConv = Sequential()
	sellModelConv.add(Conv1D(8,kernel_size= 1, strides=1,
	                 input_shape=inputShape,
	                 batch_size = None
	                   ))
	sellModelConv.add(BatchNormalization())
	sellModelConv.add(Activation('relu'))


	sellModelConv.add(Conv1D(4, kernel_size= 2, strides=1))
	sellModelConv.add(BatchNormalization())
	sellModelConv.add(Activation('relu'))

	sellModelConv.add(Conv1D(8,kernel_size= 2, strides=1))
	sellModelConv.add(BatchNormalization())
	sellModelConv.add(Activation('relu'))

	sellModelConv.add(GlobalAveragePooling1D())
	 ########################################
	sellModelLSTM = Sequential()
	sellModelLSTM.add(Permute((2, 1), input_shape=inputShape))
	sellModelLSTM.add(LSTM(4))
	sellModelLSTM.add(Dropout(0.5))
	#############################

	sellModel = Sequential()
	sellModel.add(Merge([buyModelConv, buyModelLSTM],mode='concat'))
	sellModel.add(Dense(1,activation='sigmoid'))


	# In[940]:


	# sellModel.summary()
	sellModel.compile(loss=binary_crossentropy,
	              optimizer=SGD(lr=learnRate),
	              metrics=['accuracy'])


	# In[941]:


	sellModel.fit(x=[xTrain,xTrain],
	             y=yTrain, 
	             class_weight=classWeight,
	             validation_data = ([xVal,xVal],yVal),
	             epochs = 5,
	             verbose = 0)


	# In[942]:


	score = sellModel.evaluate([xTest,xTest], yTest, verbose=0)
	print('Test loss:', score[0])
	print('Test accuracy:', score[1])


	# In[943]:


	buyModel.save('buyModel.h5')
	sellModel.save('sellModel.h5')


	# # Implement backtester

	# In[944]:


	import backtrader as bt
	from kiteconnect import KiteConnect
	import datetime as dt
	import pytz
	import math

	# b = load_model('buyModel.h5')
	# s = load_model('sellModel.h5')


	# In[945]:


	#Basic API setup
	# kite = KiteConnect(api_key="l3zela16irfa6rax")
	# data = kite.request_access_token("ldcuznh4fqg5k2w0hrtdubmga4xr43q6", secret="qefc9t3ovposnzvvy94k3sckna7vwuxs")


	# In[946]:


	# endDate = utc.localize(dt.datetime(2017,3,31))
	# # endDate+dt.timedelta(days=1)
	# # endDate
	# finDat = dat[(dat['datetime'] > endDate+dt.timedelta(days=1)) & (dat['datetime'] < endDate+dt.timedelta(days=7))]


	# In[947]:


	class neuralModel(bt.Indicator):
	    lines = ('Ind',)
	    params = (('period', 30),('neuralModel',None))

	    def __init__(self):
	        self.addminperiod(self.params.period)
	        self.i = 0

	    def next(self):
	        data = self.data.get(size=self.p.period) # get the data
	        data = np.array(data) # put it in a numpy array
	        data = skp.scale(data)
	        data = data.reshape(1, -1,1) # get it ready for the neural network
	        self.lines.Ind[0] = np.rint(self.p.neuralModel.predict([data,data])) # predict and round to 0 for no action and 1 for buy

	        


	# In[948]:


	class TestStrategy(bt.Strategy):
	    params = (
	        ('lagPeriod', lag),
	        ('buyNeural',buyModel),
	        ('SellNeural',sellModel)
	    )

	    def __init__(self):

	        self.dataclose = self.datas[0].close
	        
	        self.neuralBuy = neuralModel(
	            self.datas[0], 
	            period=self.params.lagPeriod, 
	            neuralModel = self.params.buyNeural
	        )
	        
	        self.neuralSell = neuralModel(
	            self.datas[0], 
	            period=self.params.lagPeriod, 
	            neuralModel = self.params.SellNeural
	        )


	    def next(self):

	        if self.neuralBuy[0] == 1: 
	            buyOrd = self.buy_bracket(limitprice=self.dataclose+0.4,
	                                      price=self.dataclose,
	                                      stopprice=self.dataclose-0.5,
	                                      size = 200,
	                                      valid = 0
	                                     )




	        elif self.neuralSell[0] == 1:
	            sellOrd = self.sell_bracket(limitprice=self.dataclose-0.3,
	                          price=self.dataclose,
	                          stopprice=self.dataclose+0.5,
	                          size = 200,
	                          valid = 0)


	#     def stop(self):
	#         self.close()


	# In[949]:


	class Plotter(bt.plot.Plot):

	    def __init__(self):
	        super().__init__()  # custom color for volume up bars 

	    def show(self):
	        mng = plt
	#         plt.figure(figsize=(14, 6))
	        title = str(backTestStart.date()) + " to " + str(backTestEnd.date()) 
	        plt.title(title)
	        plt.tight_layout()
	        plt.savefig("plots/"+title)
	        # plt.show()


	# In[950]:


	fed = bt.feeds.GenericCSVData(dataname='data/HFCL.csv',
	                              dtformat="%Y-%m-%dT%H:%M:%S%z",
	                              openinterest=-1,
	                              headers=False,
	                              fromdate= backTestStart,
	                              todate= backTestEnd,
	#                               timeframe=bt.TimeFrame.Minutes,
	#                               tzinput = pytz.timezone('Asia/Kolkata'),
	                              plot=False)


	cerebro = bt.Cerebro()
	cerebro.broker.setcommission(commission=0.0001)
	cerebro.adddata(fed)
	cerebro.addstrategy(TestStrategy)
	cerebro.addobserver(bt.observers.Value)
	# cerebro.addanalyzer(bt.analyzers.Returns , _name='Returns')
	print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
	thestrats = cerebro.run(stdstats=False)
	# cerebro.addobserver(bt.observers.Broker)
	# cerebro.addobserver(bt.observers.Value)
	thestrat = thestrats[0]

	# print('Sharpe Ratio:', thestrat.analyzers.Returns.get_analysis())

	print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
	cerebro.plot(start=backTestStart , end=backTestEnd,plotter = Plotter())
	portVals.append(cerebro.broker.getvalue())

import pickle

with open('objs.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
    pickle.dump(portVals,f)

	