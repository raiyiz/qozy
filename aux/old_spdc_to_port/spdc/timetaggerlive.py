# Code by Ilija Funk, last edited 13.07.2025, version 0.1
# This class establishes a connection to the Swabian Instruments TimeTagger and allows for data retrieval.
# Needs numpy, and the TimeTagger module.

import TimeTagger
import numpy as np

class timetagger_device:

	def connect(self):
		self.tagger = TimeTagger.createTimeTagger() #connects to first available TT
		print("Connected TimeTagger\n")


	def setup_sm(self):		
		self.sm = TimeTagger.SynchronizedMeasurements(self.tagger) #Allows for synchronizing multiple measurement classes in a way that ensures all these measurements to start, stop simultaneously and operate on exactly the same time tags
		self.sm_tagger = self.sm.getTagger() #Returns a proxy tagger object which can be passed to the constructor of a measurement class to register the measurements at initialization to the synchronized measurement object. Those measurements will not start automatically.


	def disconnect(self):
		TimeTagger.freeTimeTagger(self.tagger)
		print("Disconnected TimeTagger\n")


	def setup_channel(self, channel, delay):
		'''
		channel:	int of channel number
		delay:		float in ns
		'''
		self.tagger.setTriggerLevel(channel, 0.1)
		self.tagger.setInputDelay(channel, delay*1e3)


	def setup_counters(self, channel_list, CountsBinwidth, CountsTimeFrame):
		'''
		channel_list:		list of int corresponding to channels that are measured (real and virtual ones)
		CountsBinwidth:		int in ms
		CountsTimeframe:	float in s
		'''		
		CountsBinNumber = np.ceil(CountsTimeFrame*1e3/CountsBinwidth)
		self.counter = TimeTagger.Counter(self.sm_tagger, channel_list, CountsBinwidth*1e9, CountsBinNumber)


	def setup_countrates(self, channels):
		self.countrate = TimeTagger.Countrate(self.sm_tagger, channels)


	def setup_coincidences(self, a_channels, b_channels, CoinTimeWindow):
		'''
		a_channels:			list of int corresponding to connected channels of Alice
		b_channels:			list of int corresponding to connected channels of Bob
		CoinTimeWindow:		float in ns
		'''		
		coin_channel_list = []
		coin_channel_combinations = []
		for a in a_channels:
			for b in b_channels:
				coin_channel_combinations.append([a,b])
		
		self.coin = TimeTagger.Coincidences(self.sm_tagger, coin_channel_combinations, CoinTimeWindow*1e3)
		coin_channel_list = list(self.coin.getChannels())

		return coin_channel_combinations, coin_channel_list
	

	def setup_correlations(self, a_channels, b_channels, CorrBinWidth, CorrTimeFrame):
		'''
		a_channels:			list of int corresponding to connected channels of Alice
		b_channels:			list of int corresponding to connected channels of Bob
		CorrBinwidth:		float in ns
		CorrTimeFrame:		int in ns
		'''
		CorrBinNumber = np.ceil(CorrTimeFrame/CorrBinWidth)
		corr_list = []
		#for a in a_channels:
		for b in b_channels:
			corr_list.append(TimeTagger.Correlation(self.sm_tagger, a_channels[0], b, CorrBinWidth*1e3, CorrBinNumber))
		self.corrs = corr_list


	def get_counter_data(self):
		new_values = np.array(self.counter.getData())
		new_index = np.array(self.counter.getIndex())
		new_data = np.vstack((new_index, new_values))
		return new_data


	def get_corr_data(self):
		new_datas = []
		for i in range(4):
			corr = self.corrs[i]
			new_values = np.array(corr.getData())
			new_index = np.array(corr.getIndex())
			new_data = np.vstack((new_index, new_values))
			corr.clear() #clear buffer because it acumulates over time
			new_datas.append(new_data)
		return new_datas
	

	def get_countrate_data(self):
		new_data = np.array(self.countrate.getData())
		self.countrate.clear()
		return new_data


	def get_total_counts(self):
		new_data = np.array(self.countrate.getCountsTotal())
		return new_data


	def start_sm(self):
		self.sm.start()


	def stop_sm(self):
		self.sm.stop()
	

	def measure_for_sm(self,TimeFrame):
		'''
		TimeFrame:		float in s, duration of measurement
		'''
		self.sm.startFor(TimeFrame*1e12, clear=True)
		self.sm.waitUntilFinished()

	

