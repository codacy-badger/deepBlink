// Get user input
print("Please select the directory with labeled images...");
pathin = getDirectory("Choose directory");

// Create output directory
pathout = pathin + "labels/";
File.makeDirectory(pathout);

// Get file lists
filelist = getFileList(pathin);
print("Found " + lengthOf(filelist) + " files");

for (i = 0; i < lengthOf(filelist); i++) {
    if (endsWith(filelist[i], ".tif")) { 
		print("Processing: " + filelist[i]);
    	
    	// Open images
        open(pathin + filelist[i]);

		// Change Fiji's strange default values
		run("Set Scale...", "distance=0 known=0 pixel=1 unit=pixel");
		run("Set Measurements...", "  redirect=None decimal=9");

        // Generate a list of spots
        run("Measure");

		// Save output to file
		bname = replace(filelist[i], ".tif", ".csv");
		fnameout = pathout + bname;
		saveAs("Results", fnameout);

		// Close opened windows
		selectWindow("Results"); 
        run("Close" );
		selectImage(nImages());  
		run("Close");
    } 
}

print("Processing complete!");