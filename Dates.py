import pandas as pd

#I had a dataset of camera trapping in Nepal's Chitwan National park. There was a set of cameras near a road and the others were inside the park.
#There was a need to fix the setting up and removal date of the cameras in the park, as some had pictures dated before their set up date or after their removal date.
#As such, this script found the oldest and most recent picture date for each camera ID and adjusted their set up and removal date to include these dates, if needed.

parserFunc = lambda x: pd.to_datetime(x, format='%Y-%m-%d') #All dates are in ISO format YYYY-MM-DD
nepalData = pd.read_csv("G:/Work/Clara/Presenças/Nepal All Presences Dates To Fix.csv", parse_dates = ["StartDate","EndDate","pdate"], date_parser=parserFunc, low_memory= False)

#StartDate - Camera set up date
#EndDate - Camera removal date
#pdate - Picture date

daysBefore = (nepalData["StartDate"] - nepalData["pdate"]).dt.days #Get the number of days between the camera set up date and the picture date. If positive, the picture was taken before the supposed set up date.
daysAfter = (nepalData["EndDate"] - nepalData["pdate"]).dt.days #Get the number of days between the camera removal date and the picture date. If negative, the picture was taken after the supposed removal date.

distinctCameras = nepalData.loc[nepalData["ParkRoad"] == "Park","cameraID"].unique() #Only the park cameras need fixing, so gather the list of unique camera IDs in the park

for cam in distinctCameras:

    maxDaysBefore = max(daysBefore[nepalData["cameraID"]==cam]) #Gets the maximum number of days before the setup this camera has a picture for.
    if maxDaysBefore > 0:
        nepalData.loc[nepalData["cameraID"]==cam,"StartDate"] = nepalData.loc[nepalData["cameraID"]==cam,"StartDate"] - pd.to_timedelta(maxDaysBefore,unit='d') #Corrects the date if needed for all entries of that camera
        print("Camera "+cam+"'s setup date was moved "+ str(abs(maxDaysBefore))+" days back.") #Warns of the changes made to the file

    maxDaysAfter = min(daysAfter[nepalData["cameraID"]==cam]) #Gets the maximum number of days after setup this camera has a picture for.   
    if maxDaysAfter < 0:
        nepalData.loc[nepalData["cameraID"]==cam,"EndDate"] = nepalData.loc[nepalData["cameraID"]==cam,"EndDate"] - pd.to_timedelta(maxDaysAfter,unit='d')  #Corrects the date if needed for all entries of that camera
        print("Camera "+cam+"'s removal date was moved "+str(abs(maxDaysAfter))+" days forward.") #Warns of the changes made to the file        
    
nepalData["Duration"] = (nepalData["EndDate"] - nepalData["StartDate"]).dt.days # Calculates the number of total days the camera was left in the field. 

#For the statistical model to run, there was also need to create filler data so that for all days that a camera was up there was at least one entry.
nepalData.loc[nepalData["Cam"].isna(),"Cam"] = nepalData.loc[nepalData["Cam"].isna(),"cameraID"]
distinctCameras = nepalData["Cam"].unique()

for cam in distinctCameras:
   
    nepalData = nepalData.append(nepalData[nepalData["Cam"]==cam].iloc[0])
    nepalData.iloc[len(nepalData)-1] = nepalData.iloc[len(nepalData)-1]["spp"] = "Filler absence" ##A CORRIGIR https://stackoverflow.com/questions/32258817/how-to-set-a-value-in-a-pandas-dataframe-by-mixed-iloc-and-loc
    nepalData.iloc[len(nepalData)-1] = nepalData.iloc[len(nepalData)-1]["pdate"] = nepalData.iloc[0]["StartDate"] + pd.to_timedelta(range(0,nepalData.iloc[0]["Duration"]+1,1),unit='d') #Creates a list of all dates for this camera
    

nepalData.explode("pdate", ignore_index=True)

# nepalData.iloc[0]["StartDate"]
nepalData["DayOfUptime"] = (nepalData["pdate"]-nepalData["StartDate"]).dt.days+1 #Calculates how many days the camera had been setup for when each picture was taken and the overall time.

print("Writing output file...")
nepalData.to_csv("G:/Work/Clara/Presenças/Nepal All Presences Dates Fixed.csv")
print("Done!")