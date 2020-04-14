#!/usr/bin/env python3
###
#   This software module to:
#   A. Parse the vehicle path data collected through traversing WZ lanes
#       A.1 construct node points for representing lane geometry for both approach and WZ lanes 
#           a. WZ map - Read collected vehicle path data file - lat,lon,elev,heading,speed,time, and few other elements
#           a. reference point - start of WZ   
#           b. approach lane geometry
#           b. WZ lane geometry 
#       A.2 Lane attributes
#           a. Lane closures (both offset from RP and nodeAttributeXYlist of taperToLeft and taperToRight
#           b. Support of opening of the closed lane up to 4 times
#           c.Presence of workers at designated area (zone) support of up to 4 zones 
#       A.3 WZ length
#       A.4 eventID, Duration, speed limits. etc.
#
#   B. Construct .exer (XML Format) file for WZ as prescribed in ASN.1 for RSM (SAE J2945/4 WIP) including:
#   C. Construct .js (javaScript) file containing several arrays for visualization overlay on Google Satellite map

#
#   By J. Parikh / Nov, 2017
#   Revised June 2018
#   Revised Aug  2018
#
#   Ver 2.0 -   Proposed new RSM/XML(EXER) for ASN.1 and map visualization
#
###

import  os.path
import  subprocess

###
#     Open and read csv file...    
###

import  csv                                             #csv file processor
import  datetime                                        #Date and Time methods...
import  time                                            #do I need time???
import  math                                            #math library for math functions
import  random                                          #random number generator
import  xmltodict                                       #dict to xml converter
import  json                                            #json manipulation

from    wz_vehpath_lanestat_builder import buildVehPathData_LaneStat

from    wz_map_constructor  import getLanePt            #get lat/lon points for lanes 
from    wz_map_constructor  import getEndPoint          #calculates lat/lon for an end point from distance and heading (bearing)
                                                        #   called from getLanePt
from    wz_map_constructor  import getDist              #get distance in meters between pair of lat/lon points
                                                        #   called from getLanePt

###
#   Folllowing modules create:
#   .exer file (xml format) for based on ASN.1 definition for RSM as proposed to SAE for J2945/4 and J2735 (Data Dictionary)
###

from wz_xml_builder         import build_xml_CC         #common container
from wz_xml_builder         import build_xml_WZC        #WZ container
from rsm_2_wzdx_translator  import wzdx_creator         #WZDx Translator

###
#   .js file cotaining several arrays and data elements to be used by javaScript processing s/w for overlaying constructed
#   map for visualization using Google Satellite view
###

from wz_jsarray_builder     import build_jsvars         #create js variables used in processing array for overlaying on Google Map
from wz_jsarray_builder     import build_jsarray        #create js array for overlaying on Google Map

from wz_msg_segmentation    import buildMsgSegNodeList  #msg segmentation node list builder


###
#   Following to get user input for WZ config file name and display output for user...
### ---------------------------------------------------------------------------------------------------------------------

###
#   User input/output for work zone map builder is created using "Tkinter" (TK Interface) module. The  Tkinter
#   is the standard Python interface to the Tk GUI toolkit from Scriptics (formerly developed by Sun Labs).
#
#   The public interface is provided through a number of Python modules. The most important interface module is the
#   Tkinter module itself.
#
#   Just import the Tkinter module to use
#
###

###

###if sys.version_info[0] == 3:
from tkinter                import *   
from tkinter                import messagebox
from tkinter                import filedialog

###
#   Following added to read and parse WZ config file
###

import  configparser                                    #config file parser


### ------------------------------------------------------------------------------------------------------------------
#
#   Local methods/functions...
###

###
#   ACTIONS... input file dialog...
###

def inputFileDialog(filename):
    global config_filename
    # filename = filedialog.askopenfilename(initialdir=".", title="Select Input File", filetypes=[("Config File","*.wzc")])
    if len(filename): 
        config_filename = filename
        configRead(filename)   
    pass

##
#   -------------- End of input_file_dialog ------------------
##


def displayStatusMsg(xPos, yPos, msgStr):

    blankStr = " "*256
    Text = Label(root,anchor='w', justify=LEFT, text=blankStr)
    Text.place(x=xPos,y=yPos)    

    Text = Label(root,anchor='w', justify=LEFT, text=msgStr)
    Text.place(x=xPos,y=yPos)    


##
#   -------------- End of display_msg_str ---------------------
##

def buildWZMap():
    if len(config_filename): 
        startMainProcess()

##
#   -------------- End of build_WZ_map ------------------------
##

def quitIt():
    
    if messagebox.askyesno("Quit", "Sure you want to quit?") == True:
        sys.exit(0)  
##
#   -------------- End of quitIt ------------------
##

def viewMapLogFile():
  
    WZ_mapLogFile = "./WZ_MapMsg/map_builder_log.txt"
    if os.path.exists(WZ_mapLogFile):
        os.system("notepad " + WZ_mapLogFile)        
    
    else:
        messagebox.showinfo("WZ Map Log File","Work Zone Map Log File " + WZ_mapLogFile + " NOT Found ...")
##
#   -------------- End of viewLogFile ------------------------
##
   
def configRead(file):
    global wzConfig
    if os.path.exists(file):
        try:
            cfg = open(file)
            wzConfig.read_file(cfg)
            cfg.close()
            getConfigVars()
		
        except Exception as e:
            messagebox.showinfo("Read Config File", "Configuration file read failed: " + file + "\n" + str(e))
    else:
        messagebox.showinfo("Read Config", "Configuration file NOT FOUND: " + file + "\n" + str(e))

###
# ----------------- End of config_read --------------------
###
#
#   Following user specified values are read from the WZ config file specified by user in WZ_Config_UI.pyw...
#
#   WZ Configuration file is parsed here to get the user input values for used by different modules/functions...
#
#   Added: Aug. 2018
#
### -------------------------------------------------------------------------------------------------------

def getConfigVars():

###
#   Following are global variables are later used by other functions/methods...
###

    global  vehPathDataFile                                 #collected vehicle path data file
    global  sampleFreq                                      #GPS sampling freq.

    global  totalLanes                                      #total number of lanes in wz
    global  laneWidth                                       #average lane width in meters
    global  lanePadApp                                      #approach lane padding in meters
    global  lanePadWZ                                       #WZ lane padding in meters
    global  dataLane                                        #lane used for collecting veh path data
    global  wzDesc                                          #WZ Description

    global  speedList                                       #speed limits
    global  c_sc_codes                                      #cause/subcause code

##
#   WZ schedule
##

    global  wzStartDate                                     #wz start date
    global  wzStartTime                                     #wz start time    
    global  wzEndDate                                       #wz end date
    global  wzEndTime                                       #wz end time
    global  wzDaysOfWeek                                    #wz active days of week


###
#   Get collected vehicle path data point .csv file name from user input saved in wz config
###

    dirName     = wzConfig['FILES']['VehiclePathDataDir']   #veh path data file directory
    fileName    = wzConfig['FILES']['VehiclePathDataFile']  #veh path data file name

###
#   Assure that the vehicle path data file directory and file name exist.
#   If NOT, ask user to go back to WZ Configuration Step and correct file location
#   This can happen if the directory/file name is changed after doing the WZ configuration step...
#
#   Added on Nov. 6, 2018
#
###
#   vehPathDataFile - input data file
###

    vehPathDataFile = dirName + "/" + fileName                          #complete file name with directory
           
    if os.path.exists(dirName) == False:
        messagebox.showinfo("Veh Path Data Dir", "Vehicle Path Data file directory:\n\n"+dirName+"\n\nNOT found, correct directory name in WZ Configuration step...")
        btnStart["state"] = "disabled"                                  #enable button to view log file...
        btnStart["bg"] = "gray75"        
        sys.exit(0)

    if os.path.exists(vehPathDataFile) == False:
        messagebox.showinfo("Veh Path Data file", "Vehicle Path Data file:\n\n"+fileName+"\n\nNOT found, correct file name in WZ Configuration step...")
        btnStart["state"] = "disabled"                                  #enable button to view log file...
        btnStart["bg"] = "gray75"        
        sys.exit(0)

###
#   Convert str from the config file to proper data types... VERY Important...
###

###
#   Get sampling frequency...
###

    sampleFreq      = int(wzConfig['SERIALPORT']['DataRate'])           #data sampling freq

###
#   Get LANE relevant information...
###

    totalLanes      = int(wzConfig['LANES']['NumberOfLanes'])           #total number of lanes in wz
    laneWidth       = float(wzConfig['LANES']['AverageLaneWidth'])      #average lane width in meters
    lanePadApp      = float(wzConfig['LANES']['ApproachLanePadding'])   #approach lane padding in meters
    lanePadWZ       = float(wzConfig['LANES']['WorkzoneLanePadding'])   #WZ lane padding in meters
    dataLane        = int(wzConfig['LANES']['VehiclePathDataLane'])     #lane used for collecting veh path data
    wzDesc          = wzConfig['LANES']['Description']                  #WZ Description

###
#   Get SPEED information...
###

    speedList       = wzConfig['SPEED']['NormalSpeed'], wzConfig['SPEED']['ReferencePointSpeed'], \
                      wzConfig['SPEED']['WorkersPresentSpeed']              
###
#   Get WZ CAUSE/SUBCAUSE Codes... Entered by the User
#
#   Cause code - 3 = Roadworks, Subcause code - (1=..., 2=..., 4=Short term stationary, 5= ... upto 255)
###

    c_sc_codes      = [int(wzConfig['CAUSE']['CauseCode']), int(wzConfig['CAUSE']['SubCauseCode'])]

###
#   Get WZ SCHEDULE Information...
###

    wzStartDate     = wzConfig['SCHEDULE']['WZStartDate']
    wzStartTime     = wzConfig['SCHEDULE']['WZStartTime']
    wzEndDate       = wzConfig['SCHEDULE']['WZEndDate']
    wzEndTime       = wzConfig['SCHEDULE']['WZEndTime']
    wzDaysOfWeek    = wzConfig['SCHEDULE']['WZDaysOfWeek']

    if wzStartDate == "":                                               #wz start date and time are mandatory
        wzStartDate = datetime.datetime.now().strftime("%Y-%m-%d")
        wzStartTime = time.strftime("%H:%M")
    pass

###
#   ------------------------- End of getConfigVars -----------------------
#
#
### --------------------------- Build .js File -----------------------------------
#
#   Open js file for writing js arrays for map data points, approach lanes points, wz lanes points and ref. point
#
#   js_outFile  - data and array for JavaScript for visualization.
#                 fixed file name in the visualization directory 
###

def build_JS_file():

    js_outFile  = "./WZ_Visualizer/RSZW_MAP_Data.js"                    #output file for java script for visualization
    jsfile      = open(js_outFile, "w")

###
#   wz description
#   reference point location
#   No of lanes
#   Lane status
#   Lane Width(m)
###

    build_jsvars (jsfile,"//\n//        --- CAMP .js file for RSZW/LC Mapping Project --- \n")
    build_jsvars (jsfile,"//        --- Data points overlay on Google Map --- \n")
    build_jsvars (jsfile,"//        --- File Created: "+cDT+" ---\n//\n")
    build_jsvars (jsfile,"//\n//   Work zone description... \n")
    build_jsvars (jsfile,"//   Mapped work zone length in meters (approach lane, wz lane)... \n")
    build_jsvars (jsfile,"//   Reference Point coordinates... \n")
    build_jsvars (jsfile,"//   no of lanes mapped for WZ...\n")
    build_jsvars (jsfile,"//   Vehicle path data lane...\n")
    build_jsvars (jsfile,"//   wz lane status...\n")
    build_jsvars (jsfile,"//   wz lane width, lane padding for approach and WZ lanes...\n//\n")
                  
    build_jsvars (jsfile,"    var wzDesc = \""+wzDesc+"\";\n")                              #wz description
    build_jsvars (jsfile,"    var wzLength = ["+str(int(wzMapLen[0]))+","+str(int(wzMapLen[1]))+"];\n") #WZ length info
    build_jsvars (jsfile,"    var wzMapDate = \""+cDT+"\";\n")                              #map created date and time
#    build_jsvars (jsfile,"    var refPoint = ["str(refPoint[0])+","+str(refPoint[1])+","+str(refPoint[2])+"];\n")  #reference point
    build_jsvars (jsfile,"    var refPoint = ["+str(refPtIdx)+","+str(refPoint[0])+","+str(refPoint[1])+","+str(refPoint[2])+"];\n")  #reference point

    build_jsvars (jsfile,"    var noLanes = "+str(laneStat[0][0])+";\n")                    #no of lanes
    build_jsvars (jsfile,"    var mappedLaneNo = "+str(dataLane)+";\n")                     #data colleted lane
    build_jsvars (jsfile,"    var laneStat = "+str(laneStat)+";\n")                         #lane status
    build_jsvars (jsfile,"    var laneWidth = "+str(laneWidth)+";\n")                       #lane width
    build_jsvars (jsfile,"    var lanePadApp = "+str(lanePadApp)+";\n")                     #lane padding for approach lanes
    build_jsvars (jsfile,"    var lanePadWZ = "+str(lanePadWZ)+";\n")                       #lane padding for wz lanes
    build_jsvars (jsfile,"    var wpStat = "+str(wpStat)+";\n")                             #workers present status
    build_jsvars (jsfile,"    var msgSegments = "+str(msgSegList[0][0])+";\n")              #number of message segments
    build_jsvars (jsfile,"    var nodesPerSegment = "+str(msgSegList[0][1])+";\n")          #number of nodes per segment per lane

###
#   Following builds list of nodes in message segments...
###

    build_jsvars (jsfile,"//\n//   List of start and end nodes for approach and wx lane nodes per message segment\n")     
    build_jsvars (jsfile,"//   Approach lane nodes are in segment #1 (always...)\n//\n")
    build_jsvars (jsfile,"    var appNodesMsgSegment = "+str(msgSegList[1])+";\n")          #number of nodes per segment per lane

    build_jsarray (jsfile,msgSegList,"//\n//  Message segmentation list... \n//\n    var msgSegList = [\n")              

###
#   Write the collected vehicle path data points array...
###

    build_jsarray (jsfile,pathPt,"//\n//  Collected vehicle data points for WZ mapping... \n"
                   "//   Veh speed, lat, lon, alt, heading \n"  
                   "//\n    var mapData = [\n")

###
#   Write the constructed approach lane data points array...
###

    build_jsarray (jsfile,appMapPt,"//\n//   Approach Lanes --- data points... \n//\n"
                   "//   The list has lat,lon,alt,lcloStat for each node for each lane +\n"
                   "//   heading + WP flag + distVec (dist from previous node) \n"  
                   "//\n    var appMapData = [\n")

###
#   Write the constructed work zone lane data points array...
###

    build_jsarray (jsfile,wzMapPt,"//\n//   Work Zone Lanes --- data points... \n//\n"
                   "//   The list has lat,lon,alt,lcloStat for each node for each lane +\n"
                   "//   heading + WP flag + distVec (dist from prev. node) \n"  
                   "//\n    var wzMapData = [\n")
    jsfile.close()


###########   ------------------------------------------------------------------------------------   ########
##
##      END of .js file build for array/variables for overlaying on Google Earth using JavaScript application...
##
###########   ------------------------------------------------------------------------------------   ########

###
#   > > > > > > > > > > > START MAIN PROCESS < < < < < < < < < < < < < < <
###
def startMainProcess():

    global  vehPathDataFile                                         #collected vehicle path data file name
    global  refPtIdx                                                #data point number where reference point is set
    global  wzLen                                                   #work zone length in meters
    global  wzMapLen                                                #Mapped approach and wz lane length in meters
    global  appHeading                                              #approach heading

    global  msgSegList                                              #WZ message segmentation list
##  global  wzMapBuiltSuccess                                       #WZ map built successful or not flag
##  wzMapBuiltSuccess = False                                       #Default set to False                                  
    
    totRows = len(list(csv.reader(open(vehPathDataFile)))) - 1      ###total records or lines in file

    logFile.write ("\n *** - "+wzDesc+" - ***\n")    
    logFile.write ("\n\n --- Processing Input File: \n\t "+vehPathDataFile+    \
                   "\n\t Total input lines: "+str(totRows)+"\n\n")

###
#
#   Call function to read and parse the vehicle path data file created by the "vehPathDataAcq.pyw"
#   to build vehicle path data array, lane status and workers presence status arrays.
#
#   refPtIdx, wzLen and appHeading values are returned in atRefPoint list...
#
#   Updated on Aug. 23, 2018
#   
###

    atRefPoint  = [0,0,0]                                           #temporary list to hold return values from function below 
    buildVehPathData_LaneStat(vehPathDataFile,totalLanes,pathPt,laneStat,wpStat,refPoint,atRefPoint,sampleFreq)
    
    refPtIdx    = atRefPoint[0]
    wzLen       = atRefPoint[1]
    appHeading  = atRefPoint[2]

###
#   Convert refPoint a list of string to float...
###

    refPoint[0] = round(float(refPoint[0]),8)
    refPoint[1] = round(float(refPoint[1]),8)
    refPoint[2] = round(float(refPoint[2]),8)

    logFile.write (" --- Start of Work Zone at Data Point: "+str(refPtIdx)+"; "     \
                   "Reference Point @ "+str(refPoint[0])+", "+str(refPoint[1])+", "+str(refPoint[2])+"\n\n")

    

###
#   ====================================================================================================
###
#    -----  Read and processed vehPathDataFile
#           Compiled pathPt, reference point and lane closures  -----
###
###
#   Function to populate Approach Lane Map points...
#
#   refPtIdx determined in the above function...
###

###
#   "laneType"              1 = Approach lanes, 2 = wz Lanes for mapping
#   "pathPt"                contains list of data points collected by driving the vehicle on one open WZ lane
#   "appMapPt/wzMapPt"      constructed node list for lane map for BIM (RSM)
#                           contains lat,lon,alt,lcloStat for each node, each lane + heading + WP flag + distVec (dist from prev. node)
#   "lanePadApp/lanePadWz"  lane padding in addition to laneWidth
#   "refPtIdx"              Data location of the reference point in pathPt array
#   "laneStat"              A two-dimensional list to hold lane status, 0=open, 1=closed.
#                               Generated from lane closed/opened marker from collected data
#                               List location [0,0,0] provides total number of lanes
#                               It holds for each lane closed/opened instance, data point index, lane number and lane status (1/0)
#   "wpStat"                list containing location where "workers present" is set/unset
#   "dataLane"              Lane on which the vehicle path data for wz mapping was collected.
#                               "dataLane" is used to derive map data for the adjacent lanes. One lane to the left of the "dataLane" and one to right in
#                               case of total 3 lanes. For more than 5 lanes, data from multiple lanes to be collected to create map for adjascent lanes
#   "laneWidth"             lane width in meters
#
#   For approach lanes, map for all lanes are created
#
#   For wz lanes, node points for map for all lanes including closed lanes are created.
#
###

    wzMapLen = [0,0]                                    #both approach and wz mapped length
    laneType = 1                                        #approach lanes
    getLanePt(laneType,pathPt,appMapPt,laneWidth,lanePadApp,refPtIdx,appMapPtDist,laneStat,wpStat,dataLane,wzMapLen)

    logFile.write (" --- Mapped Approach Lanes: "+str(int(wzMapLen[0]))+" meters\n\n")

    
###
#
#   Now repeat the above for WZ map data point array starting from the ref point until end of the WZ
#   First WZ map point closest to the reference point is the next point after the ref. point.
#
###
    
    laneType    = 2                                     #wz lanes
    getLanePt(laneType,pathPt,wzMapPt,laneWidth,lanePadWZ,refPtIdx,wzMapPtDist,laneStat,wpStat,dataLane,wzMapLen)

    logFile.write (" --- Mapped Workzone Lanes: "+str(int(wzMapLen[1]))+" meters\n\n")


###
#   print/log lane status and workers present/not present status...
###

    laneStatIdx = len(laneStat)
    if laneStatIdx > 1:                               #have lane closures...NOTE: Index 0 location is dummy value...
        logFile.write ("\n --- Start/End of lane closure Offset from the reference point ---\n")
        for L in range(1, laneStatIdx):
            stat = "Start"
            if laneStat[L][2] == 0: stat = "End"
            logFile.write ("\t "+stat+" of lane: "+str(laneStat[L][1])+" closure at data point: "+str(laneStat[L][0])+" Offset: "+ \
                           str(int(laneStat[L][3]))+" meters\n")
        pass
    pass                                            

###
#       Do for workers present/not present zone?          
###
    wpStatIdx = len(wpStat)    
    if wpStatIdx > 0:                                       #have workers present/not present
        logFile.write ("\n --- Start/End of workers present offset from the reference point ---\n")
        for w in range(0, wpStatIdx):
            stat = "End"
            if wpStat[w][1] == 1:  stat = "Start"
            logFile.write ("\t "+stat+" of workers present @ data point: "+str(wpStat[w][0])+  \
                           "; Offset: "+str(wpStat[w][2])+" meters\n")
        pass
    pass                                            

###
#   Get nodes list for each segmented message in message segmentation...
#
#   Following revised to address error in generating message segmentation
#       Revised - Jan. 22, 2019
#
#       If computed nodes per approach lane is > computed nodes per lane (Approach nodes/lane + min. 2 nodes for WZ lane in 1st segment)
#       msgSegList[0][0] is set to -1 indicating error in generating segmentation.
#
###

    msgSegList = buildMsgSegNodeList(len(appMapPt),len(wzMapPt),totalLanes)     #build message segment list

    if msgSegList[0][0] == -1:                                                  #Error
        ANPL = msgSegList[1][2]
        MNPL = msgSegList[0][1]
        logFile.write("\n\n --- ERROR ... MESSAGE SEGMENTATION ... ERROR ---\n\t"+  \
                      " The 1st message segment must be able to include all nodes for approach lane\n\t" +  \
                      " plus at atleast first 2 nodes of WZ lane\n\t" +   \
                      "\n\n --- Nodes per approach lane: "+str(ANPL)+" > allowed max nodes per lane: " +str(MNPL)+" to stay within message payload size\n\t"+ \
                      " Reduce length of vehicle path data for approach lane to no more than 1km and try again...\n\n")
        logFile.close()                                                         #stopping the program, close file so error message is saved...
        return                                                                  #return to caller                  

    else:    

        ANPL    = msgSegList[1][2]                                              #Approach lane Nodes Per Lane
        WZNPL   = msgSegList[len(msgSegList)-1][2]                              #Work zone lane Nodes Per Lane
        TNPL    = ANPL + WZNPL
        MS      = msgSegList[0][0]                                              #Constructed message segments
        NPL     = msgSegList[0][1]                                              #no of Nodes Per Lane
        logFile.write("\n\n --- Total Nodes per Lane: " +str(TNPL)+"\n\t"+      \
                      " Total Nodes per Approach Lane: "+str(ANPL)+"\n\t"+      \
                      " Total Nodes per WZ Lane: "  +str(WZNPL)+"\n\t"+         \
                      " Total message segment(s): "  +str(MS)+"\n\t"+           \
                      " Nodes per Message Segment: "+str(NPL)+"\n\n"+           \
                      " --- Message segment list: "  +str(msgSegList)+"\n\n")
    pass


###
#   Build JS File...
###

    build_JS_file()


##############################################################################################
#
# ----------------------------- END of startMainProcess --------------------------------------
#
###############################################################################################


##
#   ---------------------------- END of Functions... -----------------------------------------
##

###
#   WZ config parser object....
###

wzConfig        = configparser.ConfigParser(delimiters=('='))

###
#   --------------------------------------------------------------------------------------------------
###
#   Get current date and time...
###

cDT = datetime.datetime.now().strftime("%m/%d/%Y - ") + time.strftime("%H:%M:%S")

###
#   Map builder output log file...
###

logFile = open("./WZ_MapMsg/map_builder_log.txt", "w")         #log file
##logFile.write ("\n *** - "+wzDesc+" - ***\n")
logFile.write ("\n *** - Created: "+cDT+" ***\n")            

### --------------------------------------------------------------------------------------------------
#       Following are local variables with set default values...
#
#	Setup array for collected data for mapping, construcyed node points for approach and WZ lanes, and
#       reference point
### --------------------------------------------------------------------------------------------------

pathPt          = []			#test vehicle path data points generated by WZ_VehPathDataAcq.py module
appMapPt        = [] 		        #array to hold approach lanes map node points
wzMapPt         = []                    #array to hold wz lanes map node points
refPoint        = [0,0,0]               #Ref. point (lat, lon, alt), initial value... ONLY ONE reference point...
appHeading      = 0                     #applicable Heading to the WZ event at the ref. point. Needed for XML for RSM Message

###
#	Variables for book keeping...
###

refPtIdx        = 0                     #index into pathPt array where the reference point is...
gotRefPt        = False                 #default 

###
#	For fixed equidistant node selection for approach and WZ lanes
#
#       As of Feb. 2018 --  Node point selection based on equidistant is NO LONGER in use...
#                           Replace by dynamic node point selection based on right triangle using change in heading angle method... 
###

appMapPtDist    = 50                    #set distance in meters between map data points for approach lanes - not used in the algo.
wzMapPtDist     = 200	                #set distance in meters between map data point for WZ map - not used in the algo.

###
#	Keep track of lane status such as point where lane closed or open is marked within WZ for each lane
#       including offset from ref. pt.
#
#       Contains 4 elements - [data point#, lane#, lane status (0-open/1-closed), offset from ref. point)  
###

laneStat        = []                    #contains lane status, data point#, lane #, 0/1 0=open, 1=closed and offset from ref point.
                                        #Generated from lane closed/opened marker from colleted data
laneStatIdx     = 0                     #laneStat + lcOffset array index

###
#	Keep track of workers present status such as point where they are present and then not present at **road level**
#       including offset from the reference point
###

wpStat          = []                    #array to hold WP location, WP status and offset from ref. point default - no workers present
wpStatIdx       = 0                     #wpStat array index    

###
#       Work zone length
###

wzLen           = 0                     #init WZ length

msgSegList      = []                    #WZ message node segmentation list

files_list      = []

ctrDT   = datetime.datetime.now().strftime("%Y%m%d-") + time.strftime("%H%M%S")

config_filename = ''

##############################################################################################
#
# ---------------------------- Automatically Export Files ------------------------------------
#
###############################################################################################

def initialize_map_visualizer(config_path):
    inputFileDialog(config_path)
    buildWZMap()

initialize_map_visualizer('C:/Users/rando/OneDrive/Documents/GitHub/V2X-manual-data-collection/CAMP Tools/Config Files/wz_default_config.wzc')