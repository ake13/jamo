#!/usr/bin/env python
import asyncio, requests, glob, sys, os, time, argparse, subprocess
from shazamio import Shazam
from alive_progress import alive_bar


# Why I build this script?
# Answer because I'm to lazy to go through nested folers and albums to tag and rename files.
# The output will rename and move the files found in the sourceDir to destinationDir as such: 
#       /destinationDir/%Genre/%Artist - %SongName.mp3 and it will tag it using id3v2 (because I'm lazy)
# Tested on Debian with python 3.11.2 but it will work on any linux debian base I guess
# you need id3v2 (apt install id3v2) for now
# If it breaks something.. go to the church to confess. good luck!


# To Do:
#
#[] - add gui
#[] - add custom log path
#[] - add escaping for angry filenames
#[] - 
#[x] - add comments to code
#[x] - add onetrack albums hack 
#[x] - add mkdir for dst_dir/genre/artist
#[x] - add tagging
#[x] - add "not found" logging
#[x] - add destination path
#[x] - add opts

# Options section for passing arguments
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--destination", type=str ,help="Destination Folder for save the file(s) tagged and renamed, required",required=True)
parser.add_argument("-s", "--source", type=str ,help="Source containg the mp3 file(s), required.",required=True)
parser.add_argument("-t", "--type", type=str ,help="Search for specific music file(s), default=mp3",default="mp3")
parser.add_argument("-v", "--verbose",help="Show stdout what's going on, default false",action='store_true')
parser.add_argument("-w", "--wait", type=float ,help="Sleep Time in seconds, it may be helpful if you are doing many API calls, default 0 sec",default=0)
parser.add_argument("-max", "--maximum", type=float ,help="Max file size in MB's. To avoid waiting for onetrack mix, albums, default 30MB",default=30)
parser.add_argument("-min", "--minimum", type=float ,help="Min file size in MB's. To avoid dummy small files, used to annoy the colleques, default 1MB.",default=1)
parser.add_argument("-p", "--progressBar",help="Progress Bar Only",action='store_true',default=True)
parser.add_argument("-l", "--logpath", type=str ,help="Logpath",default=1)
args = parser.parse_args()

src_dir = args.source
dst_dir = args.destination
file_type = args.type
verbose = args.verbose
wait_time = args.wait
max_file_size = args.maximum
min_file_size = args.minimum
prog_bar = args.progressBar

if verbose:
  print(args)

# Log the tracks not found in shazam
def writeLog(dst_dir,logFilename,trackFilename):
  d = time.strftime("%Y-%m-%d %H:%M:%S")
  with open(dst_dir+"/"+logFilename+".log", "a") as log:
      log.write("["+d+"]  --- "+trackFilename+'\n')

# Autmatic tag the rename files.. but i'm to lazy now to write a class to deal with tags, so I used id3v2 :) apt-get install id3v2
def add_tag(fileName,artist,songName,genres):
  try:
      from subprocess import DEVNULL  # Python 3.
  except ImportError:
      DEVNULL = open(os.devnull, 'wb')
  p1 = subprocess.Popen(["/usr/bin/id3v2", "-D", fileName], stdout=DEVNULL, stderr=DEVNULL)
  p1.wait()
  p2 = subprocess.Popen(["/usr/bin/id3v2", "-a", artist, "-t", songName, "-g", genres, fileName ])
  p2.wait()

# Small function that parses the video url from shazam to retrive the youtube video. Just playing with things while time fly's by.
def get_youtube_url(shazam_video_url):
  req =  requests.get(shazam_video_url, timeout=10)
  return req.json()

# Using shazam from shazamio
async def get_details(mp3):
  shazam = Shazam()
  return(await shazam.recognize_song(mp3))


def non_parsed_files(file_size,files):
  if file_size >= max_file_size:
    writeLog(dst_dir,"files_larger_then_"+str(max_file_size)+"MB",files)
  if file_size <= min_file_size:
    writeLog(dst_dir,"files_smaller_then_"+str(min_file_size)+"MB",files)


def info_logs():
  os.system('clear')
  print("\n")
  print("[ PROCESS STARTED ] at:\t"+time.strftime("%Y-%m-%d %H:%M:%S")+"\n\n")
  print("Not founded tracks log:\t"+dst_dir+"/notFoundTracks.log")
  print("Excluded large files:\t"+dst_dir+"/files_larger_then_"+str(max_file_size)+"MB.log")
  print("Excluded small files:\t"+dst_dir+"/files_smaller_then_"+str(min_file_size)+"MB.log\n\n\n\n")
    
# Some parsing things. Returns a clean dict.
def parse_meta(mp3):
  start = time.time()
  loop = asyncio.get_event_loop()
  out = loop.run_until_complete(get_details(mp3))
  try:
    artist = out["track"]["subtitle"]
  except Exception:
    pass
  else:
    artist = out["track"]["subtitle"]
    title = out["track"]["title"]
    genres = out["track"]["genres"]["primary"]
    # shazam_video_url=str([ty["youtubeurl"] for ty in out["track"]["sections"] if ty["type"] == "VIDEO"])[2:-2]
    # youtube_url=str([uri["uri"] for uri in get_youtube_url(str(shazam_video_url))["actions"]])[2:-2]
  end = time.time()
  elapsed_time = end - start
  return {"artist":artist,
          "title":title,
          "genres":genres,
          "elapsed_time": elapsed_time
          }
## Progress bar with clean stdio 
def p_bar(all_files):
  info_logs()
  with alive_bar(len(all_files)) as bar:
    for file in all_files:
        file_size = os.stat(file).st_size / (1024 * 1024)
        non_parsed_files(file_size,file)
        if file_size < max_file_size and file_size > min_file_size:
          try:
            data = parse_meta(file)
          # No track found on Shazam... Log and don't touch the files.
          # Although it's possible to find the tracks in Music Shops under "What are you listing to dude?" category.
          except KeyboardInterrupt:
            print("\nBye!\n")
            sys.exit(0)
          # write not found metadata on shazam to log  
          except:
              writeLog(dst_dir,"notFoundTracks",file)
          else:
            data = parse_meta(file)
            artist = data["artist"].replace("/","-")
            title = data["title"].replace("/","-")
            genres = data["genres"]
            # videoUrl = data["videoUrl"]
            # Check if the new path including the genres exist.
            # And if it does, it will move the file there,
            # else will create and rename and move the file and tag it and show some info.
            generated_path=dst_dir+"/"+genres+"/"+artist
            generated_filename=artist+" - "+title+".mp3"
            absolute_filepath=generated_path+"/"+generated_filename
            if os.path.exists(generated_path):
              os.rename(file,generated_path+"/"+generated_filename)
              add_tag(absolute_filepath,artist,title,genres)
            else:
              os.makedirs(generated_path)
              os.rename(file,generated_path+"/"+generated_filename)
              add_tag(absolute_filepath,artist,title,genres)
        time.sleep(wait_time)
        bar()
  print ("\n\n[ PROCESS COMPLETED ] at:\t"+time.strftime("%Y-%m-%d %H:%M:%S"))
# Verbose and normal function for troubleshooting (dirty-dirty)
def st_out(all_files):
  info_logs()
  for file in all_files:
      file_size = os.stat(file).st_size / (1024 * 1024)
      non_parsed_files(file_size,file)
      if file_size < max_file_size and file_size > min_file_size:
        # Manage exceptions inluding not found metadata file and ctrl-c
        try:
          data = parse_meta(file)
          if verbose:
            print("[ OK ] --- try: "+str(data["elapsed_time"]))
        # No track found on Shazam... Log and don't touch the files.
        # Although it's possible to find the tracks in Music Shops under "What are you listing to dude?" category.
        except KeyboardInterrupt:
          print("\nBye!\n")
          sys.exit(0)
        except:
            # write not found metadata on shazam to log and print to stdio
            writeLog(dst_dir,"notFoundTracks",file)
            print("[ KO ] --- "+file+" --- Oops! track info not found on Shazam.")
        else:
          data = parse_meta(file)
          artist = data["artist"].replace("/","-")
          title = data["title"].replace("/","-")
          genres = data["genres"]
          elapsed_time = data["elapsed_time"]
          if verbose:
            print("Original filename found: "+str(file)+" - "+str(round(os.stat(file).st_size / (1024 * 1024),2))+" MB")
            print("[ OK ] --- Information found: " +str(data))
            print("[ OK ] --- API Call Time: "+str(elapsed_time))
          
          # Check if the new path including the genres exist.
          # And if it does, it will move the file there,
          # else will create and rename and move the file and tag it and show some info.
          generated_path=dst_dir+"/"+genres+"/"+artist
          generated_filename=artist+" - "+title+".mp3"
          absolute_filepath=generated_path+"/"+generated_filename
          if verbose:
            print("generated_path: "+generated_path)
            print("generated_filename: "+generated_filename)
            print("absolute_filepath: "+absolute_filepath)
          if os.path.exists(generated_path):
            os.rename(file,generated_path+"/"+generated_filename)
            add_tag(absolute_filepath,artist,title,genres)
            if verbose:
              print("Path: "+generated_path+" already exists!")
              print("New file path and name: "+absolute_filepath+"\n")
          else:
            print("[ OK ] --- "+absolute_filepath+" generated.")
            os.makedirs(generated_path)
            os.rename(file,generated_path+"/"+generated_filename)
            add_tag(absolute_filepath,artist,title,genres)
            if verbose:
              print("The new directory "+generated_path+" is created!")
              print("New file path and name: "+absolute_filepath+"\n")
      time.sleep(wait_time)
  info_logs()
  print ("\n\n[ PROCESS COMPLETED ] at:\t"+time.strftime("%Y-%m-%d %H:%M:%S"))


# aaand the main func calling the previous functions just to do something with them 
def main():
  src_dir_path = src_dir+"/**/*."+file_type
  all_files=glob.glob(src_dir_path, recursive=True)
  if prog_bar:
    p_bar(all_files)
  else:
    st_out(all_files)

   
try:
  if __name__ == "__main__":
    main()
# CTRL-C to save the day exit and funny output.
except KeyboardInterrupt:
    print("\nBye!\n")
    sys.exit(0)

