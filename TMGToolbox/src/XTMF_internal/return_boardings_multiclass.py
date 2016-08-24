#---LICENSE----------------------
'''
    Copyright 2016 Travel Modelling Group, Department of Civil Engineering, University of Toronto

    This file is part of the TMG Toolbox.

    The TMG Toolbox is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    The TMG Toolbox is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details. 

    You should have received a copy of the GNU General Public License
    along with the TMG Toolbox.  If not, see <http://www.gnu.org/licenses/>.
'''
#---METADATA---------------------
'''
Return Boardings

    Authors: nasterska
       
        
'''
#---VERSION HISTORY
'''
    0.0.1 Created on 2016-07-25 by nasterska
'''

import inro.modeller as _m
import traceback as _traceback
_MODELLER = _m.Modeller() #Instantiate Modeller once.
_util = _MODELLER.module('tmg.common.utilities')
networkResultsTool = _MODELLER.tool('inro.emme.transit_assignment.extended.network_results')

##########################################################################################################

class ReturnBoardings(_m.Tool()):
    
    version = '0.0.1'
    tool_run_msg = ""
    number_of_tasks = 1 # For progress reporting, enter the integer number of tasks here
    
    # Tool Input Parameters
    #    Only those parameters necessary for Modeller and/or XTMF to dock with
    #    need to be placed here. Internal parameters (such as lists and dicts)
    #    get initialized during construction (__init__)
    
    xtmf_ScenarioNumber = _m.Attribute(int) # parameter used by XTMF only
    xtmf_LineAggregationFile = _m.Attribute(str)
    xtmf_CheckAggregationFlag = _m.Attribute(bool)
    
    def __init__(self):
        #---Init internal variables
        self.TRACKER = _util.ProgressTracker(self.number_of_tasks) #init the ProgressTracker

        
    def page(self):
        pb = _m.ToolPageBuilder(self, title="Return MultiClass Boardings",
                     description="Cannot be called from Modeller.",
                     runnable=False,
                     branding_text="XTMF") 
        
        return pb.render()
    
    ##########################################################################################################
            
    def __call__(self, xtmf_ScenarioNumber, xtmf_LineAggregationFile):
        
        _m.logbook_write("Extracting boarding results")
        
        #---1 Set up scenario
        scenario = _m.Modeller().emmebank.scenario(xtmf_ScenarioNumber)
        if (scenario == None):
            raise Exception("Scenario %s was not found!" %xtmf_ScenarioNumber)
        if not scenario.has_transit_results:
            raise Exception("Scenario %s does not have transit assignment results" %xtmf_ScenarioNumber)              
        
        self.xtmf_LineAggregationFile = xtmf_LineAggregationFile
        #self.xtmf_CheckAggregationFlag = xtmf_CheckAggregationFlag
        
        try:
            return self._Execute(scenario)
        except Exception, e:
            msg = str(e) + "\n" + _traceback.format_exc(e)
            raise Exception(msg)
    
    ##########################################################################################################    
    
    def _Execute(self, scenario):
        
        lineAggregation = self._LoadLineAggregationFile()

        lineBoardings = self._GetLineResults(scenario)

        for PersonClass in lineBoardings:
            netSet = set([key for key in PersonClass])
            #if self.xtmf_CheckAggregationFlag:
            #self._CheckAggregationFile(netSet, lineAggregation)
        
        self.TRACKER.completeTask()
        
        self.TRACKER.startProcess(len(lineBoardings))

        allResults = []
        for PersonClass in lineBoardings:
            results = {}
            for lineId, lineCount in PersonClass.iteritems():
                if lineId == 'name':
                    results[lineId] = lineCount
                else:
                    if not lineId in lineAggregation:
                        continue #Skip unmapped lines
                    lineGroupId = lineAggregation[lineId]
            
                    if lineGroupId in results:
                        results[lineGroupId] += lineCount
                    else:
                        results[lineGroupId] = lineCount
            self.TRACKER.completeSubtask()
            allResults.append(results)
            
        print "Extracted results from Emme"
        return str(allResults)            
    
    def _LoadLineAggregationFile(self):  
        mapping = {}
        with open(self.xtmf_LineAggregationFile) as reader:
            reader.readline()
            for line in reader:
                cells = line.strip().split(',')
                key = cells[0].strip()
                val = cells[1].strip()
                mapping[key] = val
        return mapping
    
    def _GetLineResults(self, scenario):

        multiBoardings = []

        for PersonClass in scenario.transit_strategies.data["classes"]:
            with _util.tempExtraAttributeMANAGER(scenario, 'TRANSIT_SEGMENT') as ClassBoardings:

                spec=     {
                    "on_links": None,
                    "on_segments": {
                        "total_boardings": ClassBoardings.id,
                        },
                    "aggregated_from_segments": None,
                    "analyzed_demand": None,
                    "constraint": None,
                    "type": "EXTENDED_TRANSIT_NETWORK_RESULTS"
                }

                self.TRACKER.runTool(networkResultsTool, scenario = scenario, specification = spec, class_name = PersonClass['name'])
                    
                results = _util.fastLoadSummedSegmentAttributes(scenario, [ClassBoardings.id])
            
                retVal = {}
                for lineId, attributes in results.iteritems():
                    id = str(lineId)
                    retVal[id] = attributes[ClassBoardings.id]
          
            retVal['name'] = PersonClass['name']

            multiBoardings.append(retVal)

        return multiBoardings
        
    def _CheckAggregationFile(self, netSet, lineAggregation):
        aggSet = set([key for key in lineAggregation.iterkeys()])
        
        linesInNetworkButNotMapped = [id for id in (netSet - aggSet)]
        linesMappedButNotInNetwork = [id for id in (aggSet - netSet)]
        
        if len(linesMappedButNotInNetwork) > 0:
            msg = "%s lines have been found in the network without a line grouping: " %len(linesInNetworkButNotMapped)
            msg += ",".join(linesInNetworkButNotMapped[:10])
            if len(linesInNetworkButNotMapped) > 10:
                msg += "...(%s more)" %(len(linesInNetworkButNotMapped) - 10)
            print msg
            
        if len(linesMappedButNotInNetwork) > 0:
            msg = "%s lines have been found in the aggregation file but do not exist in the network: " %len(linesMappedButNotInNetwork)
            msg += ",".join(linesMappedButNotInNetwork[:10])
            if len(linesMappedButNotInNetwork) > 10:
                msg += "...(%s more)" %(len(linesMappedButNotInNetwork) - 10)
            print msg
    
    ##########################################################################################################


    @_m.method(return_type=_m.TupleType)
    def percent_completed(self):
        return self.TRACKER.getProgress()
                
    @_m.method(return_type=unicode)
    def tool_run_msg_status(self):
        return self.tool_run_msg
        