import requests
import pprint
import datetime
import time
import logging
import traceback
import os
import sys
import argparse

def sendmail(mode,textin):
	cmd = "echo "+ textin +" |mail -s 'Alert: "+ str(mode)+ "' irinarozalio@gmail.com"
	try:
		os.popen(cmd)
		return 0
	except:
		print(time.ctime() + " Fail to send mail")
		return 1

def current_status_prom(url):
	try:
		req1 = requests.get(url,timeout=10)
		if int(req1.status_code) == 200:
			print(time.ctime() + " URL: " + url[7:35] + " current state " + str(req1.status_code))
			return(str(req1.status_code))
		else:
			print(int(req1.status_code))
			print(time.ctime() + " Got error code from Prom server " + url[7:35] + " result code " + str(req1.status_code))
			sendmail("ERROR", "GOT error code from Prom server" + url[7:35] + " result code " + str(req1.status_code))
			return ("Prometheus is Down")
	except:
		print(time.ctime() + " Fail to get " + url[7:35] )
		sendmail("WARNING","Prometheus " + url[7:35] + " is Down")
		return "Prometheus is Down"


def setup_logger(logger_name, log_file, level=logging.INFO):
	l = logging.getLogger(logger_name)
	formatter = logging.Formatter('%(asctime)s : \n %(message)s')
	fileHandler = logging.FileHandler(log_file, mode='w')
	fileHandler.setFormatter(formatter)
	streamHandler = logging.StreamHandler()
	streamHandler.setFormatter(formatter)
	l.setLevel(level)
	l.addHandler(fileHandler)
	l.addHandler(streamHandler)    

def get_series_spec_name(series_spec_name):
	URL_SERIES = 'http://localhost:9090/api/v1/series?match[]={__name__=~"prometheus_engine_query_duration_seconds_(count|sum)",slice="inner_eval"}'
	r_series_name = requests.get(url = URL_SERIES)
	series_name_data = r_series_name.json()
	series_name = str(series_name_data["data"][i]["__name__"])
	return(series_name)

def get_all_series_name():
	URL_SERIES = 'http://localhost:9090/api/v1/series?match[]={__name__!=""}'
	r_series_name = requests.get(url = URL_SERIES)
	series_name_data = r_series_name.json()
	series_name = str(series_name_data["data"][i]["__name__"])
	return(series_name)

def parse_args():
	parser = argparse.ArgumentParser(description='delete_series')
	parser.add_argument('--url', default="http://localhost:9090")
	parser.add_argument('--series_name', default="promhttp_metric_handler_requests_total")
	return parser.parse_args()

def main():
	series_name = "promhttp_metric_handler_requests_total"
	ts = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
	log_dir = os.environ['HOME'] + '/prometheus_delete_series/logs'
	log_file = os.environ['HOME'] + '/prometheus_delete_series/logs/log_' + ts +'.txt'
	if not os.path.exists(log_dir):
		os.makedirs(log_dir)
	log = logging.getLogger('log')
	setup_logger('log', log_file)
	log.info('Starting Anomalous Check....')
	args = parse_args()
	series_name = args.series_name
	url = args.url
	log.info(url)
	log.info(series_name) 


	current_state_prom = current_status_prom(url)
	if current_state_prom == "Prometheus is Down":
		sys.exit(1)
	
	tz_now_5 = (datetime.datetime.now() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
	tz_now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

	tunix_now_5 = time.mktime((datetime.datetime.now() - datetime.timedelta(minutes=5)).timetuple())
	tunix_now = time.mktime(datetime.datetime.now().timetuple())

	log.info("Timestamp before 5 min is " + tz_now_5)
	log.info("Timestamp now is " + tz_now)


	URL_NOW_5 = url + '/api/v1/query?query=' + series_name + '{code="200"}&time=' + tz_now_5
	URL_NOW = url + '/api/v1/query?query=' + series_name + '{code="200"}&time=' + tz_now
	URL_DEL = url + '/api/v1/admin/tsdb/delete_series?match[]=' + series_name + '&start=' + str(tunix_now_5) + '&end=' + str(tunix_now)

	log.info("URL query before 5 min: " + series_name + " is " + URL_NOW_5)
	log.info("URL query now: " + series_name + " is " + URL_NOW)   
	

	try:
		r_now_5 = requests.get(url = URL_NOW_5)
		r_now = requests.get(url = URL_NOW)
		data_now_5 = r_now_5.json()
		data_now = r_now.json()
		int_simp_now = int(data_now["data"]["result"][0]['value'][1])
		int_simp_now_5 = int(data_now_5["data"]["result"][0]['value'][1])
		log.info("Simple before 5 min is: " + data_now_5["data"]["result"][0]['value'][1])
		log.info("Simple now is: " + data_now["data"]["result"][0]['value'][1])
		pprint.pprint(int(data_now_5["data"]["result"][0]['value'][1]))
		pprint.pprint(int(data_now["data"]["result"][0]['value'][1]))
		p = abs(float(100 - ((int_simp_now_5 * 100)/int_simp_now)))
		percent = "{0:.2f}".format(p)
		log.info("Percent is " + str(percent) + "%")	
		if p > 0.10:
			r_del = requests.post(url = URL_DEL)
			log.info("The Series: " + series_name + "-- deleted: ")
			log.info("URL delete_series:  " + URL_DEL)
			sendmail("WARNING","Prometheus Series" + url[7:35] + " is deleted " + series_name)
		else:
			log.info("There are no delete_series... Everything is ok")
	except OSError as err:
		log.info("OS error: {0}".format(err)) 
	except IndexError as err:
		log.info(err)
		log.info("list index out of range... Try Delete Series later...")
	except Exception as err:
		log.debug(err)
		log.debug(traceback.print_tb(err.__traceback__))

if __name__ == "__main__":
	main()


