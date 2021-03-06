import matplotlib.pyplot as plt
import numpy as np
from astropy.table import Table
from scipy.interpolate import CubicSpline
from scipy.ndimage import median_filter
from scipy.signal import find_peaks
from scipy.signal.windows import gaussian as gaussian_kernel
from scipy.ndimage import gaussian_filter
from collections import OrderedDict
def gauss(lams, offset, mean, sig, amp):
    return offset + (amp * np.exp(-(lams - mean) * (lams - mean) / (2 * sig * sig))) / np.sqrt(
        2 * np.pi * sig * sig)

def linear_gauss(lams, offset, linear, mean, sig, amp):
    return offset + linear * (lams - lams.min()) + (
            amp * np.exp(-(lams - mean) * (lams - mean) / (2 * sig * sig))) / np.sqrt(
        2 * np.pi * sig * sig)

def sumd_gauss(lams, offset, mean, sig1, sig2, amp1, amp2):
    return gauss(lams, offset, mean, sig1, amp1) + gauss(lams, offset, mean, sig2, amp2)

def doublet_gauss(lams, offset, mean1, mean2, sig1, sig2, amp1, amp2):
    return gauss(lams, offset, mean1, sig1, amp1) + gauss(lams, offset, mean2, sig2, amp2)


def to_sigma(s_right,  nsigma,fwhm_to_sigma,s_left):
    return nsigma * fwhm_to_sigma * (s_right - s_left)

def replace_nans(flux_array,wave_pix_multiplier = 4):
    nanlocs = np.isnan(flux_array)
    outfluxarray = flux_array.copy()
    if np.any(nanlocs):
        background = flux_array.copy()
        background[nanlocs] = 0.
        background = median_filter(median_filter(background, size=371*wave_pix_multiplier,mode='nearest'), size=371*wave_pix_multiplier,mode='nearest')
        outfluxarray[nanlocs] = background[nanlocs]
    return outfluxarray

def find_continuum(spec, pix_per_wave, csize = 701, quant = 0.9):
    modspec = np.clip(spec,-100,np.nanquantile(spec,quant))
    nanlocs = np.where(np.bitwise_not(np.isnan(modspec)))[0]
    if len(nanlocs)>0 and nanlocs[0]>0:
        modspec[:nanlocs[0]] = modspec[nanlocs[0]]
    if len(nanlocs)>0 and nanlocs[-1]<(len(spec)-1):
        modspec[nanlocs[-1]:] = modspec[nanlocs[-1]]
    medfit = buffered_smooth(modspec, csize+2, csize, 'median')
    for attempt in range(0,100,2):
        devs = (modspec-medfit)
        dev_quant = np.nanquantile(devs,quant-(attempt/200.))
        modspec[devs>dev_quant] = medfit[devs>dev_quant] + dev_quant
        medfit = buffered_smooth(modspec, csize+10, csize, 'median')
    sig = 8 * pix_per_wave
    nzpad = int(4 * sig)
    cont = buffered_smooth(medfit, nzpad, sig, 'gaussian')
    return cont + np.nanquantile(spec-cont,0.16)

def buffered_smooth(arr,bufsize,smoothsize,smoothtype):
    zeropadded = np.pad(arr, (bufsize, bufsize), 'constant',
                        constant_values=(np.median(arr[:bufsize]), np.median(arr[-bufsize:])))
    if smoothtype.lower()[0] == 'g':
        cont = gaussian_filter(zeropadded, sigma=smoothsize, order=0)[bufsize:-bufsize]
    else:
        cont = median_filter(zeropadded, size=smoothsize, mode='nearest')[bufsize:-bufsize]
    return cont
def subtract_sky_loop_wrapper(input_dict):
    return subtract_sky_loop(**input_dict)

def subtract_sky_loop(galfluxes,skyfluxes,wave_grid,galmasks,quickreturn=False):
    outgals, remaining_skies = OrderedDict(), OrderedDict()
    gconts, sconts = OrderedDict(), OrderedDict()
    maskeds = OrderedDict()
    for galfib in galfluxes.keys():
        print("\n\n",galfib)
        galflux = galfluxes[galfib]
        skyflux = skyfluxes[galfib]
        galmask = galmasks[galfib]
        outgal,remaining_sky,gcont,scont,masked = subtract_sky(galflux=galflux,skyflux=skyflux,gallams=wave_grid,\
                                                               galmask=galmask,quickreturn=quickreturn)
        outgals[galfib],remaining_skies[galfib] = outgal,remaining_sky
        gconts[galfib], sconts[galfib] = gcont,scont
        maskeds[galfib] = masked

    outdict = {'gal':outgals,'sky':remaining_skies,'gcont':gconts,'scont':sconts,'mask':maskeds}
    return outdict

def subtract_sky(galflux,skyflux,gallams,galmask,quickreturn=False):
    pix_per_wave = int(np.ceil(1/np.nanmedian(gallams[1:]-gallams[:-1])))
    continuum_median_kernalsize = 280#371

    if int(np.ceil(pix_per_wave)) % 2 == 0:
        continuum_median_kernalsize = (continuum_median_kernalsize*pix_per_wave) + 1
    else:
        continuum_median_kernalsize = continuum_median_kernalsize * pix_per_wave

    npixels = len(galflux)
    pixels = np.arange(npixels).astype(float)
    masked = galmask.copy()

    galflux = replace_nans(galflux, wave_pix_multiplier=pix_per_wave)
    skyflux = replace_nans(skyflux, wave_pix_multiplier=pix_per_wave)

    gcont = find_continuum(galflux.copy(), pix_per_wave=pix_per_wave, csize=continuum_median_kernalsize)
    scont = find_continuum(skyflux.copy(), pix_per_wave=pix_per_wave, csize=continuum_median_kernalsize)
    gal_contsub = galflux - gcont
    sky_contsub = skyflux - scont
    # plt.figure()
    # plt.plot(gallams,gcont,alpha=0.2,label='gcont')
    # plt.plot(gallams, scont, alpha=0.2, label='scont')
    # plt.plot(gallams, galflux, alpha=0.2, label='gal')
    # plt.plot(gallams, skyflux, alpha=0.2, label='sky')
    # plt.plot(gallams, gal_contsub, alpha=0.2, label='gal contsub')
    # plt.plot(gallams, sky_contsub, alpha=0.2, label='sky contsub')
    # plt.legend()
    # plt.figure()
    # plt.plot(gallams,galflux-skyflux)
    # plt.show()
    median_sky_continuum_height = np.nanmedian(scont)
    g_peak_inds, g_peak_props = find_peaks(gal_contsub, height=(gal_contsub.max() / 8, None),
                                           width=(0.5 * pix_per_wave, 8 * pix_per_wave), \
                                           threshold=(None, None),
                                           prominence=(gal_contsub.max() / 8, None), wlen=int(24 * pix_per_wave))

    if len(g_peak_inds) == 0:
        g_peak_inds, g_peak_props = find_peaks(gal_contsub, height=(gal_contsub.max() / 20, None),
                                               width=(0.5 * pix_per_wave, 8 * pix_per_wave), \
                                               threshold=(None, None),
                                               prominence=(gal_contsub.max() / 20, None), wlen=int(24 * pix_per_wave))

    ## if it still can't identify peaks OR the counts are low so we just want a quick removal, return at this point
    ## by using just a straight subtraction
    if len(g_peak_inds) == 0:
        print("Couldn't identify any peaks, returning scaled sky for direct subtraction")
        modsky = skyflux * (np.median(gcont / scont))
        outgal = gal_contsub + gcont - modsky
        return outgal, modsky, gcont, scont, masked


    for runnum in range(10):
        s_peak_inds, s_peak_props = find_peaks(sky_contsub, height=(sky_contsub.max() / 8, None), width=(0.5*pix_per_wave, 8*pix_per_wave), \
                                               threshold=(None, None),
                                               prominence=(sky_contsub.max() / 8, None), wlen=int(24*pix_per_wave))

        g_peak_inds_matched = []
        for peak in s_peak_inds:
            ind = np.argmin(np.abs(gallams[g_peak_inds] - gallams[peak]))
            g_peak_inds_matched.append(g_peak_inds[ind])

        g_peak_inds_matched = np.asarray(g_peak_inds_matched).astype(int)

        s_peak_fluxes = sky_contsub[s_peak_inds]
        g_peak_fluxes = gal_contsub[g_peak_inds_matched]
        s_peak_total_fluxes = skyflux[s_peak_inds]
        # g_peak_fluxes = galflux[g_peak_inds_matched]
        differences = g_peak_fluxes - s_peak_fluxes
        peak_ratios = differences / s_peak_total_fluxes
        # print(np.median(peak_ratios),peak_ratios)
        if np.median(peak_ratios) < 0.001:
            break
        median_ratio = 1.0+np.median(peak_ratios)

        skyflux *= median_ratio
        scont = find_continuum(skyflux.copy(), pix_per_wave=pix_per_wave, csize=continuum_median_kernalsize)
        sky_contsub = skyflux - scont

    not_masked = np.bitwise_not(galmask)
    sky_too_large = np.where(scont[not_masked][50:-50]>gcont[not_masked][50:-50])[0]
    flux_too_large = np.where(skyflux[not_masked][50:-50] > galflux[not_masked][50:-50])[0]
    if len(sky_too_large) > 0.4*len(gal_contsub[not_masked][50:-50]) and skyflux.max() > 2000. and \
        len(flux_too_large) > 0.2*len(gal_contsub[not_masked][50:-50]):

        adjusted_skyflux_ratio = np.median(gcont[not_masked][50:-50][sky_too_large]/scont[not_masked][50:-50][sky_too_large])
        skyflux *= adjusted_skyflux_ratio
        scont = find_continuum(skyflux.copy(), pix_per_wave=pix_per_wave, csize=continuum_median_kernalsize)
        sky_contsub = skyflux - scont
        print("Needed to rescale the sky because the initial adjustment was too large: ", adjusted_skyflux_ratio)

    remaining_sky = skyflux.copy()
    sprom = np.quantile(sky_contsub, 0.8)
    gprom = np.quantile(gal_contsub, 0.8)
    s_peak_inds, s_peak_props = find_peaks(sky_contsub, height=(None, None), width=(0.1*pix_per_wave, 10*pix_per_wave), \
                                           threshold=(None, None),
                                           prominence=(sprom, None), wlen=24*pix_per_wave)
    g_peak_inds, g_peak_props = find_peaks(gal_contsub, height=(None, None), width=(0.1*pix_per_wave, 10*pix_per_wave), \
                                           threshold=(None, None),
                                           prominence=(gprom, None), wlen=24*pix_per_wave)

    if quickreturn:
        outgal = gal_contsub + gcont - skyflux
        return outgal, skyflux, gcont, scont, masked


    # sky_smthd_contsub = np.convolve(sky_contsub, [1 / 15., 3 / 15., 7 / 15., 3 / 15., 1 / 15.], 'same')
    # gal_smthd_contsub = np.convolve(gal_contsub, [1 / 15., 3 / 15., 7 / 15., 3 / 15., 1 / 15.], 'same')
    sky_smthd_contsub = gaussian_filter(sky_contsub, sigma=0.25 * pix_per_wave, order=0)
    gal_smthd_contsub = gaussian_filter(gal_contsub, sigma=0.5 * pix_per_wave, order=0)
    sky_smthd_contsub = sky_smthd_contsub * sky_contsub.sum() / sky_smthd_contsub.sum()
    gal_smthd_contsub = gal_smthd_contsub * gal_contsub.sum() / gal_smthd_contsub.sum()


    outgal = gal_contsub.copy()
    line_pairs = []
    for ii in range(len(s_peak_inds)):
        pair = {}

        lam1 = gallams[s_peak_inds[ii]]
        ind1 = np.argmin(np.abs(gallams[g_peak_inds] - lam1))

        if np.abs(gallams[g_peak_inds[ind1]] - gallams[s_peak_inds[ii]]) > 3.0*pix_per_wave:
            continue

        pair['gal'] = {
            'peak': g_peak_inds[ind1], 'left': g_peak_props['left_ips'][ind1], \
            'right': g_peak_props['right_ips'][ind1] + 1, 'height': g_peak_props['peak_heights'][ind1], \
            'wheight': g_peak_props['width_heights'][ind1]
        }
        pair['sky'] = {
            'peak': s_peak_inds[ii], 'left': s_peak_props['left_ips'][ii], \
            'right': s_peak_props['right_ips'][ii] + 1, 'height': s_peak_props['peak_heights'][ii], \
            'wheight': s_peak_props['width_heights'][ii]
        }

        line_pairs.append(pair)

    print("Identified {} lines to subtract".format(len(line_pairs)))
    seen_before = np.zeros(len(outgal)).astype(bool)
    for pair in line_pairs:
        need_to_mask = False
        g1_peak = pair['gal']['peak']
        s1_peak = pair['sky']['peak']

        itterleft = int(np.min([s1_peak,g1_peak]))
        keep_going = True
        n_angs = 1
        nextset = np.arange(1, n_angs*pix_per_wave).astype(int)
        while keep_going:
            if itterleft < np.max([1,(n_angs*pix_per_wave)//2]):
                if itterleft < 0:
                    itterleft = 0
                g_select = False
                s_select = False
            elif itterleft > n_angs*pix_per_wave:
                g_select = np.any(gal_smthd_contsub[itterleft - nextset] < gal_smthd_contsub[itterleft])
                s_select = np.any(sky_smthd_contsub[itterleft - nextset] < sky_smthd_contsub[itterleft])
            else:
                to_start = itterleft
                endcut = -(n_angs-1)*pix_per_wave + to_start
                g_select = np.any(
                    gal_smthd_contsub[itterleft - nextset[:endcut]] < gal_smthd_contsub[itterleft])
                s_select = np.any(
                    sky_smthd_contsub[itterleft - nextset[:endcut]] < sky_smthd_contsub[itterleft])

            over_zero_select = True#((gal_smthd_contsub[itterleft] > -10.) & (sky_smthd_contsub[itterleft] > -10.))
            if (g_select or s_select) and over_zero_select:
                itterleft -= np.max([1,(n_angs*pix_per_wave)//2])
            else:
                keep_going = False

        itterright = int(np.max([s1_peak,g1_peak]))
        keep_going = True
        nextset = np.arange(1, n_angs*pix_per_wave).astype(int)
        while keep_going:
            if (len(pixels) - itterright) == 1:
                g_select = False
                s_select = False
            elif (len(pixels) - itterright) >= n_angs*pix_per_wave:
                g_select = np.any(gal_smthd_contsub[itterright + nextset] < gal_smthd_contsub[itterright])
                s_select = np.any(sky_smthd_contsub[itterright + nextset] < sky_smthd_contsub[itterright])
            else:
                to_end = len(pixels) - itterright - 1
                endcut = -n_angs*pix_per_wave + to_end
                g_select = np.any(
                    gal_smthd_contsub[itterright + nextset[:endcut]] < gal_smthd_contsub[itterright])
                s_select = np.any(
                    sky_smthd_contsub[itterright + nextset[:endcut]] < sky_smthd_contsub[itterright])

            over_zero_select = True#((gal_smthd_contsub[itterright] > -10.) & (sky_smthd_contsub[itterright] > -10.))
            if (g_select or s_select) and over_zero_select:
                itterright += np.max([1,(n_angs*pix_per_wave)//2])
            else:
                keep_going = False

        slower_wave_ind = int(itterleft)
        supper_wave_ind = int(itterright) + 1

        if np.any(seen_before[slower_wave_ind:supper_wave_ind]):
            # print("some of these have already been seen")
            if np.sum(seen_before[slower_wave_ind:supper_wave_ind])>(supper_wave_ind-slower_wave_ind-2):
                continue
            locs = np.where(np.bitwise_not(seen_before[slower_wave_ind:supper_wave_ind]))[0]
            # print("was: ",slower_wave_ind,supper_wave_ind)
            supper_wave_ind = slower_wave_ind + locs[-1] + 1
            slower_wave_ind += locs[0]
            # print('now: ',slower_wave_ind,supper_wave_ind)
        if slower_wave_ind == supper_wave_ind:
            print("Lower and upper inds somehow were the same. Skipping this peak")
            print("was: ",slower_wave_ind,supper_wave_ind)
            continue

        seen_before[slower_wave_ind:supper_wave_ind] = True

        # extended_lower_ind = np.clip(slower_wave_ind - 10, 0, npixels - 1)
        # extended_upper_ind = np.clip(supper_wave_ind + 10, 0, npixels - 1)

        g_distrib = gal_contsub[slower_wave_ind:supper_wave_ind].copy()
        if np.any(g_distrib<0.):
            min_g_distrib = g_distrib.min()
        else:
            min_g_distrib = 0.
        g_distrib = g_distrib - min_g_distrib
        integral_g = np.sum(g_distrib)#/pix_per_wave
        normd_g_distrib = g_distrib / integral_g

        s_distrib = sky_contsub[slower_wave_ind:supper_wave_ind].copy()
        if np.any(s_distrib < 0.):
            min_s_distrib = s_distrib.min()
        else:
            min_s_distrib = 0.
        s_distrib = s_distrib - min_s_distrib
        integral_s = np.sum(s_distrib)#/pix_per_wave

        mean_s_ppix = np.mean(s_distrib)
        mean_g_ppix = np.mean(g_distrib)
        if integral_s > (1.1 * integral_g):
            need_to_mask = True
            integral_s = (1.1 * integral_g)

        if integral_s < (0.9 * integral_g):
            need_to_mask = True
            integral_s = (0.9 * integral_g)

        if mean_s_ppix > (30.0 + mean_g_ppix):
            need_to_mask = True
            integral_s = (30.0*len(s_distrib)) + integral_g

        if mean_g_ppix > (30.0 + mean_s_ppix):
            need_to_mask = True
            integral_s = integral_g - 30.0*len(s_distrib)

        # if integral_s > 1000:
        #     print("lessgo")
        sky_g_distrib = normd_g_distrib * integral_s
        subd = gal_contsub[slower_wave_ind:supper_wave_ind].copy() - sky_g_distrib

        if len(subd) == 0:
            print(slower_wave_ind,supper_wave_ind,subd, gal_contsub[slower_wave_ind:supper_wave_ind].copy(), sky_g_distrib,normd_g_distrib, s_distrib,g_distrib)
            continue
        if np.max(subd) > 300. or np.min(subd) < -100.:
            need_to_mask = True

        if len(sky_g_distrib) > pix_per_wave:
            nkern = (0.5*pix_per_wave)
            nzpad = int(nkern * 5)
            # if supper_wave_ind+1 < len(gal_contsub):
            #     zeropadded = np.pad(subd,(nzpad,nzpad),'constant',constant_values=(outgal[slower_wave_ind-1],outgal[supper_wave_ind+1]))
            # else:
            #     zeropadded = np.pad(subd,(nzpad,nzpad),'constant',constant_values=(outgal[slower_wave_ind-1],outgal[supper_wave_ind]))
            zeropadded = np.pad(subd,(nzpad,nzpad),'constant',constant_values=(outgal[slower_wave_ind-1],0.))
            zpad_smthd = gaussian_filter(zeropadded,sigma=nkern, order=0)
            removedlineflux = zpad_smthd[nzpad:-nzpad] #* subd.sum() / np.sum(zpad_smthd[nzpad:-nzpad])
            del zeropadded,zpad_smthd#,subd
        else:
            removedlineflux = subd#gal_contsub[slower_wave_ind:supper_wave_ind].copy() - sky_g_distrib

        # 1/np.sqrt(2*np.pi*sig*sig)
        # print(*gfit_coefs,*sfit_coefs)
        outgal[slower_wave_ind:supper_wave_ind] = removedlineflux

        ## remove the subtracted sky from that remaining in the skyflux
        remaining_sky[slower_wave_ind:supper_wave_ind] = scont[slower_wave_ind:supper_wave_ind]
        maskbuffer = 2
        if need_to_mask:
            masked[(slower_wave_ind-maskbuffer):(supper_wave_ind+maskbuffer)] = True

    remaining_sky_devs = remaining_sky - scont
    twosig = np.nanquantile(np.abs(remaining_sky_devs),0.9)
    test_bools = ((remaining_sky_devs>(4*twosig)) & np.bitwise_not(masked))
    angstrom_buffer = 0.5
    if np.any(test_bools):
        # print("Found points that didn't get removed properly",np.sum(test_bools)*pix_per_wave*2*angstrom_buffer)
        locs = np.where(test_bools)[0]
        for maskiter in np.arange(int(np.floor(-angstrom_buffer*pix_per_wave)),int(np.ceil(angstrom_buffer*pix_per_wave))+1):
            it_locs = np.clip(locs+int(maskiter),0,len(masked)-1)
            masked[it_locs] = True


    outgal = outgal + gcont - remaining_sky

    return outgal, remaining_sky, gcont, scont, masked


