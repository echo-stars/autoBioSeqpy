from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Reshape, GlobalMaxPooling1D
from keras.layers import LSTM, Bidirectional
from keras.utils import np_utils
from keras import optimizers



lstm_output_size = 64
hidden_dims = 650



print('Building model...')
model = Sequential()
model.add(Reshape((2000,20),input_shape=(40000,)))
model.add(Bidirectional(LSTM(lstm_output_size,return_sequences=True)))
model.add(Bidirectional(LSTM(lstm_output_size,return_sequences=True)))
model.add(Bidirectional(LSTM(lstm_output_size,return_sequences=True)))
model.add(GlobalMaxPooling1D())
model.add(Dense(hidden_dims))
model.add(Dropout(0.5))
model.add(Activation('relu'))
model.add(Dense(6))
model.add(Activation('softmax'))

model.compile(loss = 'categorical_crossentropy',optimizer = optimizers.Adam(),metrics = ['acc'])

