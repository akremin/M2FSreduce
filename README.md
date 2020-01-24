M2FSreduce
=========

Note:
--- 
* Reduction software for Magellan M2FS spectra

* Initially forked from Dan Gifford's OSMOSreduce package used to reduce 2.4m MDM telescope slit-mask spectra.
   * Code has been significantly altered. A few subfunctions share inspiration and lines of code from the original.

* Code produced by Anthony Kremin for M2FS on the 6.5 Magellan-Clay telescope. 

Getting Started
---
The code is run from a "quickreduce file." The standard quickreduce can be run from the command
line with:

    "-m", "--maskname":  defines the name of the mask
    "-i", "--iofile":  defines the input-ouput configuration file location
    "-o", "--obsfile":   defines the observation configuration file location
    "-p", "--pipefile":  defines the pipeline configuration file location
    
Defaults are defined such that no command line arguments are needed 
if the pipeline.ini file is in the same directory as the quickreduce
script or in a ./configs subdirectory *and* a mask is defined in the pipeline.ini file.
If non-standard naming is used for the obs and io configuration files those
must also be specified in the pipeline file or given as command line arguments.

The maskname can be used alone if standards for the three configuration file is used.
That standard is as follows:

    ./configs/pipeline.ini
    ./configs/obs_{maskname}.ini
    ./configs/io_{maskname}.ini

**Note:** The pipeline.ini file defines the locations of the data, supplementary data, and
where you want the data products to be stored. These must be edited
properly for your system before you can run. It also defines the steps run through
the pipeline and additional options passed to pipeline functions. The defaults
have the script running the initial steps through rough wavelength
calibration, stopping just before the user-input portion of the reduction.
Steps can be made false, but the data for a successful completion of that step must exist.
You should rerun all steps in a relevant chain, e.g. if you rerun debiasing you
must also re-stitch the images. Otherwise the pipeline will crash. If you try to 
Start after the stitching on your next run, your old stitched files will be accessed
and the new debiased files won't be propagated.

Example Data
--------
Configuration files are provided for one sample cluster. 
In order to run this, you must download the dataset from the
following link: https://drive.google.com/file/d/1pryyUpEYfWiTjRLG59Ur-zd99-cngOxJ/view?usp=sharing .

Overview of Steps Performed
--------
The basic steps performed by the code (A=Automatic, H=Some Human Input) are as follows:

 1. Define everything, load the bias files, generate any directories that don't exist. (A)
 2. Create master bias file, Save master bias file.  (A) 
 3. Open all other files, subtract the master bias, save  (*c?.b.fits). (A)
 3. Stitch the four opamps together. (A)
 4. Remove cosmics from all file types except bias  (*c?.bc.fits).  (A)
 9. Use fibermaps or flats to identify apertures of each spectrum. (A)
 9. Use fitted apertures to cut out 2-d spectra in thar,comp,science,twiflat. (A)
 10. Collapse the 2-d spectra to 1-d. (A)
 4. Perform a rough calibration using low-res calibration lamps. (A)
 4. Use the rough calibrations to identify lines in a higher density calibration lamp (e.g. ThAr). (H)
 5. Fit a fifth order polynomial to every spectrum of each camera for each exposure. (A)
 5. Save fits for use as initial guesses of future fits. (A)
 5. Create master skyflat file, save. (A)
 6. Open all remaining types and divide out master flat, then save  (*c?.bcf.fits). (A)
 13. Create master sky spectra by using a median fit of all sky fibers. (A)
 13. Remove continuums of the science and sky spectra and iteratively remove each sky line. (A)
 13. Subtract the sky continuum from the science continuum and add back to the science. (A)
 14. Combine the multiple sky subtracted, wavelength calibrated spectra from the multiple exposures. (A)
 15. Fit the combined spectra to redshfit using cross-correlation with SDSS templates. (A)

