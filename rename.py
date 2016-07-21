"""Script that renames .mp3 files inside an album directory according to
simple rule:

01. Trackname.mp3. Script should auto generate a folder as: (2014) Album
and copy the old files over, renamed according to the rule above. The 
purpose is to replace "conventional" file name formats like
01-artist-trackname.mp3, 01-artist-album_trackname.mp3, etc. Additionally, 
searches www.discogs.com and retrieves the album cover
"""

'''
#TODO: 
-figure out method for multi-CD album
    -on function CopyFiles(...)
-add unicode exceptions for all windows characters exceptions
-recursively delete album if not all songs copied completely

'''
import sys
import os
import subprocess
import shutil
import time
import requests
from requests.packages import urllib3
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup
from PIL import Image

#Location of default file viewing software
imageSoftwarePath = "C:\Windows\System32\mspaint.exe"
imageSoftware = "mspaint.exe"
sys.path.append(imageSoftwarePath)

#Length of time to display image preview on screen
previewTime = 2

#Default paths for downloads / music directories
sourceDir = "C:\Users\derek\Downloads"
destDir = "D:\Music"
compDir = os.path.normpath("D:\\Music\\Compilations")


#Suppress insecure request warning from discogs.com
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#URL to discogs homepage
http = urllib3.PoolManager()
discogsURL = "http://www.discogs.com"

#Various format searches to try
searchParamURLs = ["&format_exact=CD&type=all",
                   "&format_exact=Album&type=all"]

#Extensions for wanted/valid file tpyes
sngExts = [".mp3", ".flac"]

#messages for command prompt
msgDirList  = "\nList of elements in directory "
msgAlbExist = "Album directory already exists. I hope this is a multi-CD..."
msgArtistNF = " not found. Creating directory at: "
msgAlbSrch  = "Enter search term for album cover on discogs: "
msgExclu    = "Enter exclusion term, or 0 to continue: "
msgAltArt   = "\nIs compilation album? (y/n): "
msgDelSel   = "\nSelect element to delete: "
msgDelConf  = " will be deleted.\nAre you sure? (y/n): "
msgSel1     = "\n#: go into directory"
msgSel2     = "y: Select current directory for file copying/renaming"
msgSel3     = "b: Go back to downloads directory"
msgSel4     = "d: delete folder/element"


def PrintGetDir(dirPath):
    """Prints the elements within a given directory, and returns
    as a list

    Args:
        dirPath: path of the directory
    Returns: 
        fileList: list of elements in directory
    """
    print(msgDirList + dirPath + "\n")
    fileList = os.listdir(dirPath)
    for i in range(0, len(fileList)):
        num = "(" + str(i+1) + ")"
        file = fileList[i]
        print ('{:<6}{}'.format(num, file))
    return fileList

def MakeAlbumDir(dirPath):
    """Creates the directory in which the album files resides. If the
    artist directory does not already exit, the artist folder is created.

    Args:
        dirPath: path of the directory to put the album directory
    Returns:
        artistName: name of the artist
        albumName: name of the album 
        albumPath: path of the album directory 
    """
    artistName = raw_input("\nEnter artist name: ")
    if (dirPath == compDir):
        artistPath = compDir
    else:                       
        artistPath = os.path.join(dirPath, artistName)
        if not os.path.exists(artistPath):                   
            os.mkdir(artistPath)
            print("Artist " + artistName + msgArtistNF + artistPath)

    albumYear = raw_input("Enter album year: ")
    albumName = raw_input("Enter album name: ")
    albumDir = "(" + albumYear + ") " + albumName
    albumPath = os.path.join(artistPath, albumDir)
    try:
        os.mkdir(albumPath)
    except WindowsError:
        print msgAlbExist
    return artistName, albumName, albumPath

def GetAlbumPage(album, artist=""):
    """Finds and returns an album page on discogs

    Args:
        album: name of album
        artist: artist name
    Returns:
        0: could not find the album
        albumURL: the URL to the album page on discogs
    """
    albumSearch = album.replace(" ", "+")
    if (artist):
        albumSearch += "+" + artist.replace(" ", "+")
    albumURL = ""
    for searchParam in searchParamURLs:
        searchURL = discogsURL + "/?q=" + albumSearch + searchParam
        searchRequest = http.request('GET', searchURL)
        soup = BeautifulSoup(searchRequest.data, "html.parser")
        searchResults = soup.find_all("h4")
        for result in searchResults:
            searchTitle = result.find_all("a")[0]['title']
            if (album in searchTitle):
                link = result.find_all("a")[0]['href']
                if '/master/' in link:
                    albumURL = discogsURL + link
                    return albumURL
                elif '/release/' in link:
                    albumURL = discogsURL + link
                    return albumURL

    return albumURL
    
def GetAlbumSongs(albumURL):
    """Gets a tracklist of songs from a given album page on discogs

    Args:
        albumURL: the URL to the album page on discogs
    Returns:
        trackList: list of tracks on the album
    """
    albumRequest = http.request('GET', albumURL)
    soup = BeautifulSoup(albumRequest.data, "html.parser")
    pageTrackList = soup.find_all("table", class_="playlist")
    trackList = []
    songs = pageTrackList[0].find_all("span", class_="tracklist_track_title")
    for i in range(len(songs)):
        trackList.append(songs[i].text)

    return trackList

def PreviewImage(rawImage):
    """Creates a temporary file, then runs a subprocess that opens the 
    image in an image viewing software. The image will be displayed for
    a defined wait time, then the subprocess is kill, and the temporary
    file is deleted.

    Args:
        rawImage: the raw image data to display
    """
    with open('temp.jpg', 'wb') as tempFile:
        shutil.copyfileobj(rawImage, tempFile)
    tempFile.close()
    processImageView = subprocess.Popen([imageSoftware, 'temp.jpg'])
    time.sleep(previewTime)
    processImageView.kill()
    os.remove('temp.jpg')

def GetAlbumCover(albumURL, albumPath=""):
    """Finds an album's image page on www.discogs.com, goes through each
    image, and prompts the user to select which one to choose as the
    cover.

    Args:
        albumURL: URL to the album's page on discogs
        albumPath: path to the location to place album cover
    """

    #Retrieve the link to the images page for the album
    albumRequest = http.request('GET', albumURL)
    soupAlbum = BeautifulSoup(albumRequest.data, "html.parser")
    imagePageCont = soupAlbum.find_all("div", class_="image_gallery")[0]
    imagePageLink = imagePageCont.find_all("a")[0]['href']
    imagePageURL = discogsURL + imagePageLink

    #Get all HTML with a "span" containing an image
    imagePageRequest = http.request('GET', imagePageURL)
    soupImage = BeautifulSoup(imagePageRequest.data, "html.parser")
    imageSpans = soupImage.find_all("span", class_="thumbnail_link")

    #Return if no images found
    if not imageSpans:
        print "Could not find any images on album's image page"
        return

    #Show found images one by one. At each, prompt user if they want
    #to select it. If user selects, copy the image to the album directory
    for i in range(len(imageSpans)):
        imageURL = imageSpans[i].find_all("img")[0]['src']
        imageObject = requests.get(imageURL, stream=True)
        imageRaw = imageObject.raw
        PreviewImage(imageRaw)
        
        selPrefix = "Image %s of %s: " %(i+1, len(imageSpans))
        selPrompt = "Select this image? 0-No / 1-Yes: "
        select = int(raw_input(selPrefix + selPrompt))
        if select:
            imageFormat = ".%s" %(imageURL.rsplit(".", 1)[1])
            imageFileName = "cover%s" %(imageFormat)
            imagePath = os.path.join(albumPath, imageFileName)
            imageObj = requests.get(imageURL, stream=True)

            with open(imagePath, 'wb') as coverFile:
                shutil.copyfileobj(imageObj.raw, coverFile)
            coverFile.close()
            print "\nSuccess! Cover found and copied to \n\t%s\n" %(imagePath)
            return
        

    print "\nAll images were previewed, but none were saved as a cover\n"

def FormatSongUnicode(songName):
    """
    """
    pass
        
def CopyFiles(albumPath, trackList, folderPath):
    """Copies song from downloads folder into created album folder

    Args:
        albumPath: Path of newly created album folder
        trackList: proper tracklist of the album
        folderPath: Path of source folder with songs
        disc: Disc number; 0 means just one disc (no disc info)
    Returns:
        0: if no files were copied
        1: if any files were copied
    """
    copied = False
    track = 1
    for sourceFile in os.listdir(folderPath):
        songCopied = False
        for sngExt in sngExts:
            if sourceFile.endswith(sngExt.lower()):
                source = os.path.join(folderPath, sourceFile)
                songName = trackList[track-1]
                if (0):
                    pass
                    #NEED SHIT HERE FOR MULTI DISC
                else:
                    trackNum = str(track) if track > 9 else "0" + str(track)
                    songFile = "%s. %s%s" %(trackNum, songName, sngExt.lower()) 
                dest = os.path.join(albumPath, songFile)
                shutil.copy(source, dest)
                copied = True
                songCopied = True
                track += 1
                print ('{:<50}{:<8}{}'.format(songFile, " <---- ", sourceFile))
        if not songCopied:
            print ("File ignored: " + sourceFile)

    print("\nSuccess! Files copied to: \n\t%s\n" %(albumPath))
    return copied

def Browse(folderPath, defaultSrc, defaultDst, albumPath):
    """Interacts with the terminal, getting user input to select 
    directories for copying / deleting, and displaying the contents
    of a selected folder

    Args:
        folderPath: path of directory to inspect
        defaultSrc: default path of directory of downloaded albums
        defaultDst: default path of directory to place renamed albums
    Returns:
        folderPath: directory of next folder to inspect
        albumPath: path of created album directory, if it exists
    """

    dirList = PrintGetDir(folderPath)
    print(msgSel1)
    print(msgSel2)
    print(msgSel3)
    print(msgSel4)
    selection = raw_input("0 to quit: ")

    #Quit
    if (selection == "0"):                                             
        sys.exit(0)

    #Return to downloads directory  
    elif (selection == "b"):
        return defaultSrc, ""

    #Select current directory to rename / copy  
    elif (selection == "y"):
        isCompilation = raw_input(msgAltArt)
        if (isCompilation):
            artist, album, albumPath = MakeAlbumDir(compDir)
        else:
            artist, album, albumPath = MakeAlbumDir(defaultDst)
        albumURL = GetAlbumPage(album, artist)
        if (albumURL):
            trackList = GetAlbumSongs(albumURL)
            CopyFiles(albumPath, trackList, folderPath)
            GetAlbumCover(albumURL, albumPath)
        else:
            os.rmdir(albumPath)
            print "\n\nCould not find album page on discogs\n"
        return defaultSrc, ""

    #Delete folder  
    elif (selection == "d"):
        delSelect = raw_input(msgDelSel)
        delPath = os.path.join(folderPath, dirList[int(delSelect)-1])
        delConf = raw_input("\n%s%s" %(delPath, msgDelConf))
        if (delConf == "y"):
            if os.path.isdir(delPath):      #Recursively delete directory
                shutil.rmtree(delPath)
                print "\nDirectory deleted: \n\t%s\n" %(delPath)
            elif os.path.isfile(delPath):   #Delete file
                os.remove(delPath)
                print "\nFile deleted: \n\t%s\n" %(delPath)
        return defaultSrc, ""

    #Go into directory selection    
    else:
        print selection
        return os.path.join(folderPath, dirList[int(selection)-1]), ""
    

defSrc = os.path.normpath(sourceDir)
defDst = os.path.normpath(destDir)
folderPath = defSrc
albumPath = ""

#Actual script action
while (1):
    folderPath, albumPath = Browse(folderPath, defSrc, defDst, albumPath)