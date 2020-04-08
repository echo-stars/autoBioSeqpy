# -*- coding: utf-8 -*-
"""
Created on Mon May 20 21:06:26 2019

@author: jingr

processing the modeling 
"""

import os, sys, re
sys.path.append(os.path.curdir)
sys.path.append(sys.argv[0])

helpDoc = '''
The predicting script for using built model. 

Usage python predicting.py --dataTestFilePaths File1 File2 ... --paraFile filepath --predictionSavePath name [--verbose 0/1]

The ‘--dataTestFilePaths’ is the testdataset, the format is the same as the dataset for training.

The ‘--paraFile’ is the file recording the related parameters (could be extract by adding --paraSaveName when using running.py), this script will load the model according to the parameters.

The '--predictionSavePath' is the outfile which contain the predictions, otherwise the predictions will be printed to STDOUT


'''
import paraParser
if '--help' in sys.argv:
    print(helpDoc)
    exit()

import moduleRead
import dataProcess
#import analysisPlot
import numpy as np
#from sklearn.metrics import accuracy_score,f1_score,roc_auc_score,recall_score,precision_score,confusion_matrix,matthews_corrcoef 
import tensorflow as tf
from utils import TextDecorate, evalStrList
td = TextDecorate()

paraDictCMD = paraParser.parseParameters(sys.argv[1:])

paraFile = paraDictCMD['paraFile']
if not paraFile is None:
    paraDict = paraParser.parseParametersFromFile(paraFile)
    paraDict['dataTestFilePaths'] = paraDictCMD['dataTestFilePaths']
    paraDict['dataTestModelInd'] = paraDictCMD['dataTestModelInd']
else:
    paraDict = paraDictCMD.copy()


#parameters
#dataType = paraDict['dataType']
dataTypeList = paraDict['dataType']
dataEncodingType = paraDict['dataEncodingType']
spcLen = paraDict['spcLen']
firstKernelSize = paraDict['firstKernelSize']
#dataTrainFilePaths = paraDict['dataTrainFilePaths']
#dataTrainLabel = paraDict['dataTrainLabel']
dataTestFilePaths = paraDict['dataTestFilePaths']
dataTestLabel = paraDict['dataTestLabel']
#modelLoadFile = paraDict['modelLoadFile']
#weightLoadFile = paraDict['weightLoadFile']
dataSplitScale = paraDict['dataSplitScale']
outSaveFolderPath = paraDict['outSaveFolderPath']
showFig = paraDict['showFig']
saveFig = paraDict['saveFig']
savePrediction = paraDict['savePrediction']

loss = paraDict['loss']
optimizer = paraDict['optimizer']
if not optimizer.startswith('optimizers.'):
    optimizer = 'optimizers.' + optimizer
if not optimizer.endswith('()'):
    optimizer = optimizer + '()'
metrics = paraDict['metrics']

shuffleDataTrain = paraDict['shuffleDataTrain']
shuffleDataTest = paraDict['shuffleDataTest']
batch_size = paraDict['batch_size']
epochs = paraDict['epochs']

#useKMer = paraDict['useKMer']
#KMerNum = paraDict['KMerNum']
inputLength = paraDict['inputLength']
modelSaveName = paraDict['modelSaveName']
weightSaveName = paraDict['weightSaveName']
noGPU = paraDict['noGPU']
labelToMat = paraDict['labelToMat']


modelLoadFile = paraDict['modelLoadFile']
useKMerList = paraDict['useKMer']
if len(useKMerList ) == 0:
    useKMerList = [False] * len(modelLoadFile)
KMerNumList = paraDict['KMerNum']
if len(KMerNumList ) == 0:
    KMerNumList = [3] * len(modelLoadFile)
    
#dataTrainModelInd = paraDict['dataTrainModelInd']
#if len(modelLoadFile) == 1:
#    dataTrainModelInd = [0] * len(dataTrainFilePaths)
dataTestModelInd = paraDict['dataTestModelInd']
if len(modelLoadFile) == 1:
    dataTestModelInd = [0] * len(dataTestFilePaths)
    
modelPredictFile = outSaveFolderPath + os.path.sep + modelSaveName



weightLoadFile = outSaveFolderPath + os.path.sep + weightSaveName

verbose = paraDict['verbose']

predictionSavePath = None
for i,k in enumerate(sys.argv):
    if k == '--predictionSavePath':
        predictionSavePath = sys.argv[i+1]
    elif k == '--verbose':
        verbose = sys.argv[i+1]


if noGPU:
    if verbose:
        print('As set by user, gpu will be disabled.')
    os.environ["CUDA_VISIBLE_DEVICES"] = '-1'
else:
    #check the version of tensorflow before configuration
    tfVersion = tf.__version__
    if int(tfVersion.split('.')[0]) >= 2:
#        config = tf.compat.v1.ConfigProto(allow_growth=True)
        config = tf.compat.v1.ConfigProto()
        config.gpu_options.allow_growth = True

        sess =tf.compat.v1.Session(config=config)
    else:
        config = tf.ConfigProto(gpu_options=tf.GPUOptions(allow_growth=True))
        sess = tf.Session(config=config)


if not len(dataTypeList) == len(modelLoadFile):
    if verbose:
        td.printC('Please provide enough data type(s) as the number of --modelLoadFile','r')
assert len(dataTypeList) == len(modelLoadFile)

featureGenerators = []
for i,subDataType in enumerate(dataTypeList):
    if subDataType.lower() == 'protein':
        if verbose:
            td.printC('Enconding protein data for model %d ...' %i,'b')
        featureGenerator = dataProcess.ProteinFeatureGenerator(dataEncodingType[i], useKMer=useKMerList[i], KMerNum=KMerNumList[i])
    elif subDataType.lower() == 'dna':
        if verbose:
            td.printC('Enconding DNA data for model %d ...' %i,'b')
        featureGenerator = dataProcess.DNAFeatureGenerator(dataEncodingType[i], useKMer=useKMerList[i], KMerNum=KMerNumList[i])
    elif subDataType.lower() == 'rna':
        if verbose:
            td.printC('Enconding RNA data for model %d ...' %i,'b')
        featureGenerator = dataProcess.RNAFeatureGenerator(dataEncodingType[i], useKMer=useKMerList[i], KMerNum=KMerNumList[i])
    elif subDataType.lower() == 'other':
        if verbose:
            td.printC('Reading CSV-like data for model %d ...' %i,'b')
        featureGenerator = dataProcess.OtherFeatureGenerator()
    else:
        td.printC('Unknow dataType %r, please use \'protein\', \'dna\' ,\'rna\' or \'other\'' %subDataType, 'r')
    featureGenerators.append(featureGenerator)
    assert subDataType.lower() in ['protein','dna','rna','other']

#if dataType is None:
#    if verbose:
#        print('NO data type provided, please provide a data type suce as \'protein\', \'dna\' or\'rna\'')
#assert not dataType is None
#
#if dataType.lower() == 'protein':
#    if verbose:
#        print('Enconding protein data...')
#    featureGenerator = dataProcess.ProteinFeatureGenerator(dataEncodingType, useKMer=useKMer, KMerNum=KMerNum)
#elif dataType.lower() == 'dna':
#    if verbose:
#        print('Enconding DNA data...')
#    featureGenerator = dataProcess.DNAFeatureGenerator(dataEncodingType, useKMer=useKMer, KMerNum=KMerNum)
#elif dataType.lower() == 'rna':
#    if verbose:
#        print('Enconding RNA data...')
#    featureGenerator = dataProcess.RNAFeatureGenerator(dataEncodingType, useKMer=useKMer, KMerNum=KMerNum)
#else:
#    print('Unknow dataType %r, please use \'protein\', \'dna\' or\'rna\'' %dataType)
#assert dataType.lower() in ['protein','dna','rna']




if verbose:
    print('test datafiles should be provided, the test dataset will be generated from the test datafiles...')
    print('Checking the number of test files, which should be larger than 1 (e.g. at least two labels)...')
assert len(dataTestFilePaths) > 0

if verbose:
    print('Begin to generate test dataset...')

testDataLoadDict = {}    
for modelIndex in range(len(modelLoadFile)):
    testDataLoadDict[modelIndex] = []
#    testDataLoaders = []
for i,dataPath in enumerate(dataTestFilePaths):
    modelIndex = dataTestModelInd[i]
    featureGenerator = featureGenerators[modelIndex]
    dataLoader = dataProcess.DataLoader(label = 0, featureGenerator=featureGenerator)
    dataLoader.readFile(dataPath, spcLen = spcLen[modelIndex])
    testDataLoadDict[modelIndex].append(dataLoader)

testDataMats = []
testLabelArrs = []
testNameLists = []
for modelIndex in range(len(modelLoadFile)):
    testDataLoaders = testDataLoadDict[modelIndex]
    testDataSetCreator = dataProcess.DataSetCreator(testDataLoaders)
    testDataMat, testLabelArr, nameList = testDataSetCreator.getDataSet(toShuffle=False, withNameList=True)
    testDataMats.append(testDataMat)
    testLabelArrs.append(testLabelArr)
    testNameLists.append(nameList)
if verbose:
    td.printC('Test datasets generated.','g')
nameTemp = testNameLists[0]    
testDataMats, testLabelArrs, sortedIndexes = dataProcess.matAlignByName(testDataMats,nameTemp,testLabelArrs,testNameLists)
    
tmpTempLabel = testLabelArrs[0]
for tmpLabel in testLabelArrs:
    assert np.sum(np.array(tmpTempLabel) - np.array(tmpLabel)) == 0   
#
#    
#testDataLoaders = []
#for i,dataPath in enumerate(dataTestFilePaths):
#    #The label is set to 0, since we do not need the label for testing (only for accuracy calculating)
#    dataLoader = dataProcess.DataLoader(label = 0, featureGenerator=featureGenerator)
#    dataLoader.readFile(dataPath, spcLen = spcLen)
#    testDataLoaders.append(dataLoader)
#testDataSetCreator = dataProcess.DataSetCreator(testDataLoaders)
#testDataMat, testLabelArr = testDataSetCreator.getDataSet(toShuffle=shuffleDataTest)

if labelToMat:
    if verbose:
        td.printC('Since labelToMat is set, the labels would be changed to onehot-like matrix','b')
    testLabelArr,testLabelArrDict,testArrLabelDict = dataProcess.labelToMat(testLabelArrs[0])
#    print(testLabelArr)
else:
    testLabelArr = testLabelArrs[0]


    
if verbose:
#    print('Datasets generated, the scales are:\n\ttraining: %d x %d\n\ttest: %d x %d' %(trainDataMat.shape[0],trainDataMat.shape[1],testDataMat.shape[0],testDataMat.shape[1]))    
    print('begin to prepare model...')
#    print('Loading keras model from .py files...')
    

#
#if not inputLength is None:
#    if inputLength == 0:
#        inputLength = testDataMat.shape[1]



if verbose:
    print('Checking module file for modeling')
if modelPredictFile is None:
    if verbose:
        print('please provide a model file in a json file.')
if weightLoadFile is None:
    if verbose:
        print('the weight file is necessary for predicting, otherwise the model will be with initialized weight')
assert not modelPredictFile is None
assert not weightLoadFile is None

if verbose:
    print('Loading module and weight file')
model = moduleRead.readModelFromJsonFileDirectly(modelPredictFile,weightLoadFile)
if verbose:
    print('Module loaded, generating the summary of the module')
    model.summary()
#    
#if '2D' in str(model.layers[0].__class__):
#    if verbose:
#        print('2D layer detected, data will be reshaped accroding to the \'spcLen\'')    
#    if useKMer:
#        reshapeLen = spcLen - KMerNum + 1
#    else:            
#        reshapeLen = spcLen 
#    #newShape = (int(trainDataMat.shape[1]/spcLen),spcLen)
##    newShape = (int(trainDataMat.shape[1]/reshapeLen),reshapeLen)
##    trainDataMat = trainDataMat.reshape(trainDataMat.shape[0],int(trainDataMat.shape[1]/reshapeLen),reshapeLen,1)
#    testDataMat = testDataMat.reshape(testDataMat.shape[0],int(testDataMat.shape[1]/reshapeLen),reshapeLen,1)
#    

if not outSaveFolderPath is None:
    if not os.path.exists(outSaveFolderPath):        
        os.makedirs(outSaveFolderPath, exist_ok=True)
    else:
        if verbose:
            print('outpath %s is exists, the outputs might be overwirten' %outSaveFolderPath)


predicted_Probability = model.predict(testDataMats)
if not 'predict_classes' in dir(model):
    prediction = np.rint(predicted_Probability)
    if labelToMat:
        prediction = dataProcess.matToLabel(np.array(prediction,dtype=int), testArrLabelDict)
else:
    prediction = model.predict_classes(testDataMats)

if labelToMat:
    testLabelArr = dataProcess.matToLabel(testLabelArr, testArrLabelDict)
else:
    testLabelArr = testLabelArrs[0]
    
predicted_Probability = model.predict(testDataMat)
prediction = model.predict_classes(testDataMat)



if not predictionSavePath is None:
    tmpPredictSavePath = predictionSavePath
    if verbose:
        print('Saving predictions at %s' %tmpPredictSavePath)
    with open(tmpPredictSavePath, 'w') as FIDO:
        FIDO.write('#Label\tPrediction\tPobability\n')
        for i in range(len(testLabelArr)):
            tmpLabel = i
            tmpPrediction = prediction[i]
            while len(tmpPrediction.shape) > 0:
                tmpPrediction = tmpPrediction[0]
            tmpProbability = predicted_Probability[i]
#            tmpStr = '%r\t%r\t%f\n' %(tmpLabel,tmpPrediction,tmpProbability)
            if len(tmpProbability.shape) == 0:
                tmpStr = '%r\t%r\t%f\n' %(tmpLabel,tmpPrediction,tmpProbability)
            else:
                if len(tmpProbability) == 1:
                    tmpStr = '%r\t%r\t%f\n' %(tmpLabel,tmpPrediction,tmpProbability[0])
                else:
                    tmpStr = '%r\t%r\t[ %s ]\n' %(tmpLabel,tmpPrediction,' , '.join(tmpProbability.astype(str)))
            FIDO.write(tmpStr)
else:
    if verbose:
        print('No save path prvided, the predictions will be listed in STDOUT')
    print('\n\n')
    print('#Instance\tPrediction\tPobability')
    for i in range(len(testLabelArr)):
        tmpLabel = i
        tmpPrediction = prediction[i]
        while len(tmpPrediction.shape) > 0:
            tmpPrediction = tmpPrediction[0]
        tmpProbability = predicted_Probability[i]
        if len(tmpProbability.shape) == 0:
            tmpStr = '%r\t%r\t%f' %(tmpLabel,tmpPrediction,tmpProbability)
        else:
            if len(tmpProbability) == 1:
                tmpStr = '%r\t%r\t%f' %(tmpLabel,tmpPrediction,tmpProbability[0])
            else:
                tmpStr = '%r\t%r\t[ %s ]' %(tmpLabel,tmpPrediction,' , '.join(tmpProbability.astype(str)))
        print(tmpStr)
    print('\n\n')


print('Finished')