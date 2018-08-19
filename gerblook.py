'''
Original script: https://github.com/blairbonnett-mirrors/kicad/blob/master/demos/python_scripts_examples/plot_board.py
also this: https://kicad.mmccoo.com/2017/03/05/adding-your-own-command-buttons-to-the-pcbnew-gui/

Requires Beautifulsoup4 and Requests packages

'''

from __future__ import print_function
import sys
import shutil
import os
import subprocess
import requests
from bs4 import BeautifulSoup

import wx
import pcbnew

gerblook_url = "http://gerblook.org/"

def copy2clip(txt):
    cmd='echo '+txt.strip()+'|clip'
    return subprocess.check_call(cmd, shell=True)

def plotGerbers():

    board = pcbnew.GetBoard()

    pctl = pcbnew.PLOT_CONTROLLER(board)

    popt = pctl.GetPlotOptions()

    popt.SetOutputDirectory("gerbers/")

    # Set some important plot options:
    popt.SetPlotFrameRef(False)
    popt.SetLineWidth(pcbnew.FromMM(0.1))

    popt.SetAutoScale(False)
    popt.SetScale(1)
    popt.SetMirror(False)
    popt.SetUseGerberAttributes(False)
    popt.SetExcludeEdgeLayer(True)
    popt.SetPlotPadsOnSilkLayer(False)
    popt.SetScale(1)
    popt.SetUseGerberProtelExtensions(True)

    # This by gerbers only (also the name is truly horrid!)
    popt.SetSubtractMaskFromSilk(False)

    # Once the defaults are set it become pretty easy...
    # I have a Turing-complete programming language here: I'll use it...
    # param 0 is a string added to the file base name to identify the drawing
    # param 1 is the layer ID
    plot_plan = [
        ("CuTop", pcbnew.F_Cu, "Top layer"),
        ("CuBottom", pcbnew.B_Cu, "Bottom layer"),
        ("PasteBottom", pcbnew.B_Paste, "Paste Bottom"),
        ("PasteTop", pcbnew.F_Paste, "Paste top"),
        ("SilkTop", pcbnew.F_SilkS, "Silk top"),
        ("SilkBottom", pcbnew.B_SilkS, "Silk top"),
        ("MaskBottom", pcbnew.B_Mask, "Mask bottom"),
        ("MaskTop", pcbnew.F_Mask, "Mask top"),
        ("EdgeCuts", pcbnew.Edge_Cuts, "Edges"),
    ]

    for layer_info in plot_plan:
        pctl.SetLayer(layer_info[1])
        pctl.OpenPlotfile(
            layer_info[0], pcbnew.PLOT_FORMAT_GERBER, layer_info[2])
        pctl.PlotLayer()

    # At the end you have to close the last plot, otherwise you don't know when
    # the object will be recycled!
    pctl.ClosePlot()

    # Fabricators need drill files.
    # sometimes a drill map file is asked (for verification purpose)
    drlwriter = pcbnew.EXCELLON_WRITER(board)
    drlwriter.SetMapFileFormat(pcbnew.PLOT_FORMAT_PDF)

    mirror = False
    minimalHeader = False
    offset = pcbnew.wxPoint(0, 0)
    # False to generate 2 separate drill files (one for plated holes, one for non plated holes)
    # True to generate only one drill file
    mergeNPTH = True
    drlwriter.SetOptions(mirror, minimalHeader, offset, mergeNPTH)

    metricFmt = True
    drlwriter.SetFormat(metricFmt)

    # Generate drill file
    genDrl = True
    genMap = False
    drlwriter.CreateDrillandMapFilesSet(pctl.GetPlotDirName(), genDrl, genMap)
    return pctl.GetPlotDirName()

# Actionplugin class, show up in Tools->External Plugins
class GerblookPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Plot gerbers and upload to Gerblook"
        self.category = "Plotting"
        self.description = "Plot gerbers, zip them and upload to Gerblook with url copied to clipboard."

    def Run(self):
        # Generate gerbers
        gerber_folder = plotGerbers()

        # change dir to root of gerber folder and zip it
        os.chdir(os.path.dirname(os.path.dirname(gerber_folder)))
        shutil.make_archive("gerbers", "zip", "gerbers")

        # make new session to store session id
        s = requests.Session()

        # make get request to site and scrape csrf token from the html
        r = s.get(gerblook_url)
        soup = BeautifulSoup(r.text)
        csrf_token = soup.find('input', {'name': 'csrf_token'})['value']

        # data to be sent to form
        data = {'gerbers' : ('gerbers.txt', open('gerbers.zip', 'rb'), 'application/zip')}
        values= {'copper_color':"Gold", 'silkscreen_color':"White", 'soldermask_color':"Blue", 'csrf_token': csrf_token}

        # post file to form
        r = s.post(gerblook_url, files=data, data=values, allow_redirects=False)

        # find redirect url in headers
        url = r.headers['Location']
        wx.LogMessage("Link copied to clipboard: " + url)
        copy2clip(url)
        


GerblookPlugin().register()  # Instantiate and register to Pcbnew
