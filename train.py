import os
import numpy as np
import tensorflow as tf
from keras.models import Sequential
from keras.layers.advanced_activations import LeakyReLU, PReLU
from keras.optimizers import SGD, RMSprop, Adagrad

from keras.layers import Dropout, Flatten, Dense, Convolution2D, LSTM, Bidirectional, Activation, TimeDistributed, GlobalAveragePooling1D, Merge, GRU
from keras import applications
from keras.layers.normalization import BatchNormalization
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn import random_projection
from keras.callbacks import TensorBoard, EarlyStopping, ModelCheckpoint

# dimensions of our images.
#img_width, img_height = 224, 224

# fix random seed for reproducibility
np.random.seed(1200)
#train_data_dir = '/input/data/images/train'
#validation_data_dir = '/input/data/images/validation'
nb_train_samples = 14280
nb_validation_samples = 6120
instance_flag=0 #0 for loading data from Local, 1 for FloydHub instance
#MAIN
nb_train_samples = 14280
nb_validation_samples = 6120
#lstm_num_timesteps=10 #How many timesteps of features are being fed per sample of a batch. 


batch_size=10 #Samples per batch.
timesteps=6 #Timesteps per sample
#features_size=2048



global start
global starter
start=1
#Define Generator
global trainbag, validationbag
train_index_pointer = list(np.linspace(1,nb_train_samples-1, nb_train_samples, dtype=np.int64))
validation_index_pointer = list(np.linspace(1,nb_validation_samples-1, nb_validation_samples, dtype=np.int64))
trainbag=len(train_index_pointer)
validationbag=len(validation_index_pointer)


#Define Smooth L1 Loss
def l1_smooth_loss(y_true, y_pred):
    abs_loss = tf.abs(y_true - y_pred)
    sq_loss = 0.5 * (y_true - y_pred)**2
    l1_loss = tf.where(tf.less(abs_loss, 1.0), sq_loss, abs_loss - 0.5)
    return tf.reduce_sum(l1_loss, -1)

def generator(features, labels, batch_size, timesteps, flag=0):
	count=0
	#print('Generator Active')
	batch_features=np.empty((0,timesteps, features_size))
	batch_labels=np.empty((1,0))
	while True:

		if flag == 0 :
			batch_size=10
			#trainbag=len(train_index_pointer)
			#if trainbag<timesteps:
				#print("Out of Novel Train Data")
				#break
			#else:
			#index = train_index_pointer.pop(np.random.randint(1,trainbag))
			index = np.random.randint(1,nb_train_samples-1, size=1, dtype=np.int64)
			#print("Train Dataset Size", trainbag)
		else:
			batch_size=1
			#validationbag=len(validation_index_pointer)
			#if validationbag<timesteps:
				#print("Out of Validation Data")
				#break
			#else:
			#index = validation_index_pointer.pop(np.random.randint(1,validationbag))
			index = np.random.randint(1,nb_validation_samples-1, size=1, dtype=np.int64)
			#print("Validation Dataset Size", validationbag)


		#int(index, flag)		
		
		dataX = features[index,]
		dataY = labels[index,]

		#Create One sample of (timesteps, features_size)
		for j in range(1,timesteps):
			pointer = index-j
			x = features[pointer,]
			y = labels[pointer,]
			dataX = np.vstack((dataX,x))
			dataY= np.vstack((dataY,y))
			
		"""
		if flag==0:
			train_index_pointer=temp
		else:
			validation_index_pointer=temp	"""

		dataY = np.mean(dataY, axis=0)
		dataX=np.expand_dims(dataX, axis=0)
		dataY=np.expand_dims(dataY, axis=0)

		#Stack samples to create batch
		batch_features = np.vstack((batch_features,dataX))
		batch_labels = np.column_stack((batch_labels,dataY))

		count+=1
		if count == batch_size:
			count=0
			dataX=[]
			dataY=[]
			TrainY =  np.transpose(batch_labels, (1, 0))
			yield batch_features, TrainY
		
#Build Model
def buildmodel(summary):

	#Define hyperparameters
    
	lr = 0.001
	weight_init='glorot_normal'

	#Define Model
	model=Sequential()
	model.add(BatchNormalization(input_shape=(timesteps, features_size)))
	model.add(Bidirectional(GRU(32, activation='relu', kernel_initializer=weight_init, recurrent_activation='hard_sigmoid', return_sequences=True)))
	model.add(Bidirectional(GRU(128, activation='relu', kernel_initializer=weight_init, recurrent_activation='hard_sigmoid', return_sequences=False)))
	model.add(Dense(units=128, init=weight_init, bias=True))
	model.add(LeakyReLU(alpha=0.3))
	model.add(BatchNormalization())
	model.add(Dense(units=64, init=weight_init, bias=True))
	model.add(LeakyReLU(alpha=0.3))
	model.add(BatchNormalization())
	model.add(Dropout(0.5))
	model.add(Dense(units=32, init=weight_init))
	model.add(LeakyReLU(alpha=0.3))
	model.add(BatchNormalization())
	model.add(Dropout(0.2))
	model.add(Dense(16, init=weight_init))
	model.add(LeakyReLU(alpha=0.3))
	model.add(Dropout(0.2))
	model.add(Dense(1, init=weight_init, activation='linear'))


	print('Compiling Model...')
	#sgd = SGD(lr=lr, decay=1e-6, momentum=0.9, nesterov=True)
	optimize=RMSprop(lr)
	model.compile(optimizer=optimize,
		loss=l1_smooth_loss,
		metrics=['mse'])

	if summary:
		print(model.summary())
		return model
	
#Load Bottleneck Features (Resnet50) & Labels
print('Loading Bottleneck Features Data and Labels...')

if instance_flag==0:
	train_data = np.load(open('data/bottleneck_features_train.npy'))
	validation_data = np.load(open('data/bottleneck_features_validation.npy'))
	labels = np.loadtxt('data/train.txt')
	labels.astype(float)
else:
	train_data = np.load(open('/input/bottleneck_features_train.npy'))
	validation_data = np.load(open('/input/bottleneck_features_validation.npy'))
	labels = np.loadtxt('/input/train.txt')
	labels.astype(float)


#speeds = scaler.fit_transform(labels)
#speeds.astype(float)
speeds=labels
y_train= speeds[0:nb_train_samples]
y_validation= speeds[nb_train_samples:len(labels)]
x_train=np.reshape(train_data, (nb_train_samples, -1))
x_validation=np.reshape(validation_data, (nb_validation_samples, -1))

#Reduce Dimensions
transformer = random_projection.SparseRandomProjection(eps=0.5)
X_train= transformer.fit_transform(x_train)

features_size=X_train.shape[1]

transformer = random_projection.SparseRandomProjection(features_size)
X_validation=transformer.fit_transform(x_validation)

X_train.astype(float)
X_validation.astype(float)

print('Final Data Shape = [X_train, X_validation, y_train, y_validation]', X_train.shape , X_validation.shape, y_train.shape, y_validation.shape)

print('Building Model...')

model = buildmodel(summary=1)
train_generator = generator(X_train, y_train, batch_size, timesteps, 0)
validation_generator = generator(X_validation, y_validation, batch_size, timesteps, 1)


print('Training...')

earlyStopping= EarlyStopping(monitor='val_loss', patience=10, verbose=1, mode='auto')
tensorboard = TensorBoard(log_dir='./logs', histogram_freq=0,
                       write_graph=True, write_images=False)


if instance_flag==0:
	checkpointer = ModelCheckpoint(filepath="./dashcam_weights.hdf5", verbose=1, save_best_only=True)
else:
	checkpointer = ModelCheckpoint(filepath="/output/dashcam_weights.hdf5", verbose=1, save_best_only=True)

training = model.fit_generator(train_generator, steps_per_epoch=20, epochs=20, verbose=1, validation_data=validation_generator, validation_steps=10, callbacks=[tensorboard, earlyStopping, checkpointer])

print('Training Successful - Saving Weights...')

loss_history = training.history["val_loss"]
mse_history = training.history["val_mean_squared_error"]

numpy_loss_history = np.array(loss_history)
numpy_mse_history = np.array(mse_history)
np.savetxt("./loss_history.txt", numpy_loss_history, delimiter=",")
np.savetxt("./mse_history.txt", numpy_mse_history, delimiter=",")
