from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Reshape, GRU, Bidirectional, GlobalMaxPooling1D
from keras.layers import Embedding
from keras import optimizers


max_features = 26
embedding_size = 128
lstm_output_size = 64
hidden_dims = 125


print('Building model...')
model = Sequential()
model.add(Embedding(max_features,embedding_size,input_length=2000))
model.add(Bidirectional(GRU(lstm_output_size, return_sequences=True)))
model.add(GlobalMaxPooling1D())
model.add(Dense(hidden_dims))
