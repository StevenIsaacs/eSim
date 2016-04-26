import sys
import os
import re 
import json
from string import maketrans

class NgMoConverter:
    
        
    def __init__(self):
        #Loading JSON file which hold the mapping information between ngspice and Modelica.
        with open('Mapping.json') as mappingFile:
            self.mappingData = json.load(mappingFile)
            
        self.ifMOS = False
        self.sourceDetail = []
        self.deviceDetail = []
        self.subCktDetail = []
        self.inbuiltModelDetail = []
        self.deviceList = ['d','D','j','J','q','Q','m','M']
        self.sourceList = ['v','V','i','I']
        self.inbuiltModelDict = {}
        
            

    def readNetlist(self,filename):
        """
        Read Ngspice Netlist
        """
        netlist = []
        if os.path.exists(filename):
            try:
                f = open(filename)
            except Exception as e:
                print("Error in opening file")
                print(str(e))
                sys.exit()
        else:
            print filename + " does not exist"
            sys.exit()

        data = f.read()
        data = data.splitlines()
        f.close()
        for eachline in data:
            eachline=eachline.strip()
            if len(eachline)>1:
                if eachline[0]=='+':
                    netlist.append(netlist.pop()+eachline.replace('+',' ',1))
                else:
                    netlist.append(eachline)  
        return netlist
    
    def separateNetlistInfo(self,netlist):
        """
        Separate schematic data and option data
        """
        optionInfo = []
        schematicInfo = []
        
        for eachline in netlist:
            if len(eachline) > 1:
                if eachline[0]=='*':
                    continue
                elif eachline[0]=='.':
                    optionInfo.append(eachline)
                    #optionInfo.append(eachline.lower())
                elif eachline[0] in self.deviceList:
                    if eachline[0]=='m' or eachline[0]=='M':
                        self.ifMOS = True
                    schematicInfo.append(eachline)
                    self.deviceDetail.append(eachline)
                elif eachline[0]=='x' or eachline[0]=='X':
                    self.subCktDetail.append(eachline)
                elif eachline[0] in self.sourceList:
                    schematicInfo.append(eachline)
                    self.sourceDetail.append(eachline)
                elif eachline[0]=='a' or eachline[0]=='A':
                    schematicInfo.append(eachline)
                    self.inbuiltModelDetail.append(eachline)    
                else:
                    schematicInfo.append(eachline)
                    ##No need of making it lower case as netlist is already converted to ngspice
                    #schematicInfo.append(eachline.lower())
        return optionInfo,schematicInfo
    
    def addModel(self,optionInfo):
        """
        Add model parameters in the modelica file and create dictionary of model parameters
        This function extract model and subckt information along with their parameters with the help of optionInfo
        """
        modelName = []
        modelInfo = {}
        subcktName = []
        paramInfo = []
        transInfo = {}
        
        for eachline in optionInfo:
            words = eachline.split()
            if words[0] == '.include':
                name = words[1].split('.')
                if name[1] == 'lib':
                    modelName.append(name[0])
                if name[1] == 'sub':
                    subcktName.append(name[0])
            elif words[0] == '.param':
                paramInfo.append(eachline)
            elif words[0] == '.model':
                model = words[1]
                modelInfo[model] = {}
                eachline = eachline.replace(' = ','=').replace('= ','=').replace(' =','=')
                eachline = eachline.split('(')
                templine = eachline[0].split()
                trans = templine[1]
                transInfo[trans] = []
                templine[2] = templine[2].lower()
                if templine[2] in ['npn', 'pnp', 'pmos', 'nmos']:
                    transInfo[trans] = templine[2]
                else:
                    self.inbuiltModelDict[model]=templine[2]
                eachline[1] = eachline[1].lower()
                eachline = eachline[1].split()
                
                for eachitem in eachline:
                    if len(eachitem) > 1:
                        eachitem = eachitem.replace(')','')
                        iteminfo = eachitem.split('=')
                        for each in iteminfo:
                            modelInfo[model][iteminfo[0]] = iteminfo[1]
        
        #Adding details of model(external) and subckt into modelInfo and subcktInfo
        for eachmodel in modelName:
            filename = eachmodel + '.lib'
            if os.path.exists(filename):
                try:
                    f = open(filename)
                except:
                    print("Error in opening file")
                    sys.exit()
            else:
                print filename + " does not exist"
                sys.exit()
            data = f.read()
            data = data.replace('+', '').replace('\n','').replace(' = ','=').replace('= ','=').replace(' =','=')
            #data = data.lower() #Won't work if Reference model name is Upper Case     
            newdata = data.split('(')
            templine_f = newdata[0].split()
            trans_f = templine_f[1]
            transInfo[trans_f] = []
            templine_f[2] = templine_f[2].lower() 
            if templine_f[2] in ['npn', 'pnp', 'pmos', 'nmos']:
                transInfo[trans_f] = templine_f[2]
                       
            refModelName = trans_f
            newdata[1] = newdata[1].lower()
            modelParameter = newdata[1].split()
            
            modelInfo[refModelName] = {}
            
            for eachline in modelParameter:
                if len(eachline) > 1:
                    eachline = eachline.replace(')','')
                    info = eachline.split('=')
                    for eachitem in info:
                        modelInfo[refModelName][info[0]] = info[1] 
            f.close()
        
        return modelName, modelInfo, subcktName, paramInfo ,transInfo
    
    def processParam(self,paramInfo):
        """
        Process parameter info and update in Modelica syntax
        """
        modelicaParam = []
        for eachline in paramInfo:
            eachline = eachline.split('.param')
            #Include ',' in between parameter
            #Removing leading and trailing space
            line = eachline[1].strip()
            line = line.split()
            final_line = ','.join(line)
            stat = 'parameter Real ' + final_line + ';'
            stat = stat.translate(maketrans('{}', '  '))
            modelicaParam.append(stat)
        return modelicaParam
    
    
    def separatePlot(self,schematicInfo):
        """
        separate print plot and component statements
        """
        compInfo = []
        plotInfo = []
        for eachline in schematicInfo:
            words = eachline.split()
            if words[0] == 'run':
                continue
            elif words[0] == 'plot' or words[0] == 'print':
                plotInfo.append(eachline)
            else:
                compInfo.append(eachline)
        return compInfo, plotInfo
    
    def separateSource(self,compInfo):
        """
        Find if dependent sources are present in the schematic and if so make a dictionary with source details
        """
        sourceInfo = {}
        source = []
        for eachline in compInfo:
            words = eachline.split()  ##This line need to be confirmed with Manas
            if eachline[0] in ['f', 'h']:
                source.append(words[3])
        if len(source) > 0:
            for eachline in compInfo:
                words_s = eachline.split()
                if words_s[0] in source:
                    sourceInfo[words_s[0]] = words_s[1:3]
        return sourceInfo
    
    def getUnitVal(self,compValue):
        #regExp = re.compile("([0-9]+)([a-zA-Z]+)")
        regExp = re.compile("([0-9]+)\.?([0-9]+)?([a-zA-Z])?")
        matchString = regExp.match(str(compValue))  #separating number and string
        try:
            valBeforeDecimal = matchString.group(1)
            valAfterDecimal = matchString.group(2)
            unitValue = matchString.group(3)
            if str(valAfterDecimal)=='None':
                modifiedcompValue = valBeforeDecimal+self.mappingData["Units"][unitValue]
            else:
                modifiedcompValue = valBeforeDecimal+'.'+valAfterDecimal+self.mappingData["Units"][unitValue]
            return modifiedcompValue
        except:
            return compValue
    
    def tryExists(self,modelInfo,words,wordNo, key,default):
        """ 
        checks if entry for key exists in dictionary, else returns default
        """
        try:
            keyval = modelInfo[words[wordNo]][key]
            keyval = self.getUnitVal(keyval)
        except KeyError:
            keyval = str(default)
        return keyval
            
        
    def compInit(self,compInfo, node, modelInfo, subcktName,dir_name,transInfo):
        """
        For each component in the netlist initialize it according to Modelica format
        """
        print "CompInfo inside compInit function : compInit------->",compInfo
        #### initial processing to check if MOs is present. If so, library to be used is BondLib
        modelicaCompInit = []
        numNodesSub = {} 
        mosInfo = {}
        IfMOS = '0'
        
        for eachline in compInfo:
            #words = eachline.split()
            if eachline[0] == 'm':
                IfMOS = '1'
                break
        if len(subcktName) > 0:
            subOptionInfo = []
            subSchemInfo = []
            for eachsub in subcktName:
                filename_tem = eachsub + '.sub'
                filename_tem = os.path.join(dir_name, filename_tem)
                data = self.readNetlist(filename_tem)
                subOptionInfo, subSchemInfo = self.separateNetlistInfo(data)
                
                for eachline in subSchemInfo:
                    #words = eachline.split()
                    if eachline[0] == 'm':
                        IfMOS = '1'
                        break
        
        #Lets Start with Source details
        for eachline in self.sourceDetail:
            words = eachline.split()
            #Preserve component name from lower case function
            compName = words[0]
            #Now Lower case all other
            words = eachline.lower().split()
            words[0] = compName
            typ = words[3].split('(')
            
            sourceType = compName[0].lower()
            
            if sourceType == 'v':
                if typ[0] == "pulse":
                    per = words[9].split(')')
                    stat = self.mappingData["Sources"][sourceType][typ[0]]+' '+compName+'(rising = '+self.getUnitVal(words[6])+', V = '+self.getUnitVal(words[4])\
                    +', width = '+self.getUnitVal(words[8])+', period = '+self.getUnitVal(per[0])+', offset = '+self.getUnitVal(typ[1])+', startTime = '+self.getUnitVal(words[5])+', falling = '+self.getUnitVal(words[7])+');'                                                                                                                                                                             
                    modelicaCompInit.append(stat)
                if typ[0] == "sine":
                    theta = words[7].split(')')
                    stat = self.mappingData["Sources"][sourceType][typ[0]]+' '+compName+'(offset = '+self.getUnitVal(typ[1])+', V = '+self.getUnitVal(words[4])+', freqHz = '+self.getUnitVal(words[5])+', startTime = '+self.getUnitVal(words[6])+', phase = '+self.getUnitVal(theta[0])+');'
                    modelicaCompInit.append(stat)
                if typ[0] == "pwl":
                    keyw = self.mappingData["Sources"][sourceType][typ[0]]+' '
                    stat = keyw + compName + '(table = [' + self.getUnitVal(typ[1]) + ',' + self.getUnitVal(words[4]) + ';'
                    length = len(words);
                    for i in range(6,length,2):
                        if i == length-2:
                            w = words[i].split(')')
                            stat = stat + self.getUnitVal(words[i-1]) + ',' + self.getUnitVal(w[0]) 
                        else:
                            stat = stat + self.getUnitVal(words[i-1]) + ',' + self.getUnitVal(words[i]) + ';'
                    stat = stat + ']);'
                    modelicaCompInit.append(stat) 
                if typ[0] == words[3] and typ[0] != "dc":
                    #It is DC constant but no dc keyword
                    val_temp = typ[0].split('v')
                    stat = self.mappingData["Sources"][sourceType]["dc"]+' ' + compName + '(V = ' + self.getUnitVal(val_temp[0]) + ');' 
                    modelicaCompInit.append(stat)
                elif typ[0] == words[3] and typ[0] == "dc":
                    stat = self.mappingData["Sources"][sourceType][typ[0]]+' ' + compName + '(V = ' + self.getUnitVal(words[4]) + ');'    ### check this
                    modelicaCompInit.append(stat)
                    
            elif sourceType=='i':
                stat = self.mappingData["Sources"][sourceType]["dc"]+' '+compName+'(I='+self.getUnitVal(words[3])+');'
                modelicaCompInit.append(stat)
                
                
        #Lets start for device
        for eachline in self.deviceDetail:
            words=eachline.split()
            deviceName = eachline[0].lower()
            if deviceName=='d':
                if len(words)>3:
                    if modelInfo[words[3]].has_key('n'):
                        n = float(modelInfo[words[3]]['n'])
                    else:
                        n = 1.0
                    vt = str(float(0.025*n))
                    #stat = self.mappingData["Devices"][deviceName]["import"]+' '+ words[0] + '(Ids = ' + modelInfo[words[3]]['is'] + ', Vt = ' + vt + ', R = 1e12' +');'
                    start = self.mappingData["Devices"][deviceName]["import"]
                    stat = start+" "+words[0]+"("
                    tempstatList=[]
                    userDeviceParamList=[]
                    refName = words[-1]
                    for key in modelInfo[refName]:
                        #If parameter is not mapped then it will just pass                         
                        try:
                            actualModelicaParam = self.mappingData["Devices"][deviceName]["mapping"][key]
                            tempstatList.append(actualModelicaParam+"="+self.getUnitVal(modelInfo[refName][key])+" ")
                            userDeviceParamList.append(str(actualModelicaParam))
                        except:
                            pass
                    #Adding Vt and R
                    userDeviceParamList.append("Vt")
                    tempstatList.append("Vt="+vt)
                    #Running loop over default parameter of OpenModelica
                    for default in self.mappingData["Devices"][deviceName]["default"]:
                        if default in userDeviceParamList:
                            continue
                        else:
                            defaultValue = self.mappingData["Devices"][deviceName]["default"][default]
                            tempstatList.append(default+"="+self.getUnitVal(defaultValue)+" ")
                    
                    stat += ",".join(str(item) for item in tempstatList)+");"   
                                        
                else:
                    stat = self.mappingData["Devices"][deviceName]["import"]+" "+ words[0] +";"
                modelicaCompInit.append(stat)
                
            elif deviceName=='q':
                trans = transInfo[words[4]]
                if trans == 'npn':
                    start = self.mappingData["Devices"][deviceName]["import"]+".NPN"
                elif trans == 'pnp':
                    start = self.mappingData["Devices"][deviceName]["import"]+".PNP"
                else:
                    print "Transistor "+trans+" Not found"
                    sys.exit(1)
                
                stat = start+" "+words[0]+"("
                tempstatList=[]
                userDeviceParamList=[]
                refName = words[4]
                for key in modelInfo[refName]:
                    #If parameter is not mapped then it will just pass                         
                    try:
                        if key=="vaf":
                            inv_vak = float(self.getUnitVal(modelInfo[refName][key]))
                            vak_temp = 1/inv_vak
                            vak = str(vak_temp)
                            tempstatList.append("Vak="+vak+" ")
                            userDeviceParamList.append(str("Vak"))
                        else:
                            actualModelicaParam = self.mappingData["Devices"][deviceName]["mapping"][key]
                            tempstatList.append(actualModelicaParam+"="+self.getUnitVal(modelInfo[refName][key])+" ")
                            userDeviceParamList.append(str(actualModelicaParam))
                    except:
                        pass
                #Running loop over default parameter of OpenModelica
                for default in self.mappingData["Devices"][deviceName]["default"]:
                    if default in userDeviceParamList:
                        continue
                    else:
                        defaultValue = self.mappingData["Devices"][deviceName]["default"][default]
                        tempstatList.append(default+"="+self.getUnitVal(defaultValue)+" ")
                        
                stat += ",".join(str(item) for item in tempstatList)+");" 
                modelicaCompInit.append(stat)
                
            elif deviceName=='m':
                eachline = eachline.split(words[5])
                eachline = eachline[1]
                eachline = eachline.strip()
                eachline = eachline.replace(' = ', '=').replace('= ','=').replace(' =','=').replace(' * ', '*').replace(' + ', '+').replace(' { ', '').replace(' } ', '')
                eachline = eachline.split()
                mosInfo[words[0]] = {}
                for each in eachline:
                    if len(each) > 1:
                        each  = each.split('=')
                        mosInfo[words[0]][each[0]] = each[1]
                trans = transInfo[words[5]]
                
                if trans == 'nmos':
                    start = self.mappingData["Devices"][deviceName]["import"]+".Mn"
                elif trans=='pmos' :
                    start = self.mappingData["Devices"][deviceName]["import"]+".Mp"
                else:
                    print "MOSFET "+trans+" not found"
                    sys.exit(1)
                    
                
                stat = start+" "+words[0]+"("
                tempstatList=[]
                userDeviceParamList=[]
                refName = words[5]
                
                for key in modelInfo[refName]:
                    #If parameter is not mapped then it will just pass                   
                    try:
                        if key=="uo":
                            U0 = str(float(self.getUnitVal(modelInfo[refName][key]))*0.0001)
                            tempstatList.append("U0="+U0+" ")
                            userDeviceParamList.append(str("U0"))
                        else:
                            actualModelicaParam = self.mappingData["Devices"][deviceName]["mapping"][key]
                            tempstatList.append(actualModelicaParam+"="+self.getUnitVal(modelInfo[refName][key])+" ")
                            userDeviceParamList.append(str(actualModelicaParam))
                    except Exception as err:
                        print str(err)
                
                #Running loop over default parameter of OpenModelica
                for default in self.mappingData["Devices"][deviceName]["default"]:
                    if default in userDeviceParamList:
                        continue
                    else:
                        defaultValue = self.mappingData["Devices"][deviceName]["default"][default]
                        tempstatList.append(default+"="+self.getUnitVal(defaultValue)+" ")
                        
                               
                #Adding LEVEL(This is constant not the device levele)
                tempstatList.append("LEVEL=1"+" ")
                
                try:
                    l = mosInfo[words[0]]['l']
                    tempstatList.append("L="+self.getUnitVal(l)+" ")
                except KeyError:
                    tempstatList.append("L=1e-6"+" ")
                try:
                    w = mosInfo[words[0]]['w']
                    tempstatList.append("W="+self.getUnitVal(w)+" ")
                except KeyError:
                    tempstatList.append("W=100e-6"+" ")
                try:
                    As = mosInfo[words[0]]['as']
                    ad = mosInfo[words[0]]['ad']
                    tempstatList.append("AS="+self.getUnitVal(As)+" ")
                    tempstatList.append("AD="+self.getUnitVal(ad)+" ")
                except KeyError:
                    tempstatList.append("AS=0"+" ")
                    tempstatList.append("AD=0"+" ")
                try:
                    ps = mosInfo[words[0]]['ps']
                    pd = mosInfo[words[0]]['pd']
                    tempstatList.append("PS="+self.getUnitVal(ps)+" ")
                    tempstatList.append("PD="+self.getUnitVal(pd)+" ")
                except KeyError:
                    tempstatList.append("PS=0"+" ")
                    tempstatList.append("PD=0"+" ")
                                
                stat += ",".join(str(item) for item in tempstatList)+");" 
                modelicaCompInit.append(stat)
        
        #Lets start for inbuilt model of ngspice
        for eachline in self.inbuiltModelDetail:
            words=eachline.split()
            userModelParamList = []
            refName = words[-1]
            actualModelName = self.inbuiltModelDict[refName]
            
            start = self.mappingData["Models"][actualModelName]["import"]
            stat = start +" "+ words[0]+"("
            tempstatList=[]
            
            for key in modelInfo[refName]:
                #If parameter is not mapped then it will just pass 
                try:
                    actualModelicaParam = self.mappingData["Models"][actualModelName]["mapping"][key]
                    tempstatList.append(actualModelicaParam+"="+self.getUnitVal(modelInfo[refName][key])+" ")
                    userModelParamList.append(str(actualModelicaParam))
                except:
                    pass
                
            #Running loop over default parameter of OpenModelica
            for default in self.mappingData["Models"][actualModelName]["default"]:
                if default in userModelParamList:
                    continue
                else:
                    defaultValue = self.mappingData["Models"][actualModelName]["default"][default]
                    tempstatList.append(default+"="+self.getUnitVal(defaultValue)+" ")
                    
            stat += ",".join(str(item) for item in tempstatList)+");"
            modelicaCompInit.append(stat)  
        
        
        #Lets start for Subcircuit
        for eachline in self.subCktDetail:
            global point
            global subname
            temp_line = eachline.split()
            temp = temp_line[0].split('x')
            index = temp[1]
            for i in range(0,len(temp_line),1):
                if temp_line[i] in subcktName:
                    subname = temp_line[i]
                    numNodesSub[subname] = i - 1
                    point = i
            if len(temp_line) > point + 1:
                rem = temp_line[point+1:len(temp_line)]
                rem_new = ','.join(rem)
                stat = subname + ' ' + subname +'_instance' + index + '(' +  rem_new + ');'
            else:
                stat = subname + ' ' + subname +'_instance' + index + ';'
            modelicaCompInit.append(stat)
                                         
        
        for eachline in compInfo:
            words = eachline.split()
            #val = words[3]
            #value = self.splitIntoVal(val)
            value = self.getUnitVal(words[-1])
            if eachline[0] == 'r':
                stat = 'Analog.Basic.Resistor ' + words[0] + '(R = ' + value + ');'
                modelicaCompInit.append(stat)
            elif eachline[0] == 'c':
                stat = 'Analog.Basic.Capacitor ' + words[0] + '(C = ' + value + ');'
                modelicaCompInit.append(stat)
            elif eachline[0] == 'l':
                stat = 'Analog.Basic.Inductor ' + words[0] + '(L = ' + value + ');'
                modelicaCompInit.append(stat) 
            elif eachline[0] == 'e':
                stat = 'Analog.Basic.VCV ' + words[0] + '(gain = ' + self.getUnitVal(words[5]) + ');'
                modelicaCompInit.append(stat) 
            elif eachline[0] == 'g':
                stat = 'Analog.Basic.VCC ' + words[0] + '(transConductance = ' + self.getUnitVal(words[5]) + ');'
                modelicaCompInit.append(stat) 
            elif eachline[0] == 'f':
                stat = 'Analog.Basic.CCC ' + words[0] + '(gain = ' + self.getUnitVal(words[4]) + ');'
                modelicaCompInit.append(stat) 
            elif eachline[0] == 'h':
                stat = 'Analog.Basic.CCV ' + words[0] + '(transResistance = ' + self.getUnitVal(words[4]) + ');'
                modelicaCompInit.append(stat)
                                 
            else:
                continue
            
        if '0' or 'gnd' in node:
            modelicaCompInit.append('Analog.Basic.Ground g;')
        return modelicaCompInit, numNodesSub
    
    def getSubInterface(self,subname,numNodesSub):
        """
        Get the list of nodes for subcircuit in .subckt line
        """
        subOptionInfo_p = []
        subSchemInfo_p = []
        filename_t = subname + '.sub'
        data_p = self.readNetlist(filename_t)
        subOptionInfo_p, subSchemInfo_p = self.separateNetlistInfo(data_p)
        if len(subOptionInfo_p) > 0:
            newline = subOptionInfo_p[0]
            newline = newline.split('.subckt '+ subname)       
            intLine = newline[1].split()
            newindex = numNodesSub[subname]
            nodesInfoLine = intLine[0:newindex]
        return nodesInfoLine
    
    def getSubParamLine(self,subname, numNodesSub, subParamInfo,dir_name):
        """
        Take subcircuit name and give the info related to parameters in the first line and initislise it in
        """
        #nodeSubInterface = []
        subOptionInfo_p = []
        subSchemInfo_p = []
        filename_t = subname + '.sub'
        filename_t = os.path.join(dir_name, filename_t)
        data_p = self.readNetlist(filename_t)
        subOptionInfo_p, subSchemInfo_p = self.separateNetlistInfo(data_p)
        
        if len(subOptionInfo_p) > 0:
            newline = subOptionInfo_p[0]
            newline = newline.split('.subckt '+ subname)       
            intLine = newline[1].split()
            newindex = numNodesSub[subname]
            appen_line = intLine[newindex:len(intLine)]
            appen_param = ','.join(appen_line)
            paramLine = 'parameter Real ' + appen_param + ';'
            paramLine = paramLine.translate(maketrans('{}', '  '))
            subParamInfo.append(paramLine)
        return subParamInfo
    
    def nodeSeparate(self,compInfo, ifSub, subname, subcktName,numNodesSub):
        """
        separate the node numbers and create nodes in modelica file; 
        the nodes in the subckt line should not be inside protected keyword. pinInit is the one that goes under protected keyword.
        """
        node = []
        nodeTemp = []
        nodeDic = {}
        pinInit = 'Modelica.Electrical.Analog.Interfaces.Pin '
        pinProtectedInit = 'Modelica.Electrical.Analog.Interfaces.Pin '
        protectedNode = []
        #print "CompInfo coming to nodeSeparate function: compInfo",compInfo
        
        #Removing '[' and ']' from compInfo for Digital node
        for i in range(0,len(compInfo),1):
            compInfo[i] = compInfo[i].replace("[","").replace("]","")
            #Remove "-" from node as it does not work in modelica
            compInfo[i] = compInfo[i].replace("-","")
        
                
        for eachline in compInfo:
            words = eachline.split()
            if eachline[0] in ['m', 'e', 'g', 't','M','E','G','T']:
                nodeTemp.append(words[1])
                nodeTemp.append(words[2])
                nodeTemp.append(words[3])
                nodeTemp.append(words[4])
            elif eachline[0] in ['q', 'j','J','Q']:
                nodeTemp.append(words[1])
                nodeTemp.append(words[2])
                nodeTemp.append(words[3])
            elif eachline[0]=='x' or eachline[0]=='X':
                templine = eachline.split()
                for i in range(0,len(templine),1):
                    if templine[i] in subcktName:
                        point = i   
                nodeTemp.extend(words[1:point])
            else:
                nodeTemp.append(words[1])
                nodeTemp.append(words[2])
        for i in nodeTemp:
            if i not in node:
                node.append(i)
        
            
        for i in range(0, len(node),1):
            nodeDic[node[i]] = 'n' + node[i]
            if ifSub == '0':
                if i != len(node)-1:
                    pinInit = pinInit + nodeDic[node[i]] + ', '
                else:
                    pinInit = pinInit + nodeDic[node[i]]
            else:
                nonprotectedNode = self.getSubInterface(subname, numNodesSub) 
                if node[i] in nonprotectedNode:
                    continue
                else:
                    protectedNode.append(node[i])
        if ifSub == '1':
            if len(nonprotectedNode) > 0:
                for i in range(0, len(nonprotectedNode),1):
                    if i != len(nonprotectedNode)-1:
                        pinProtectedInit = pinProtectedInit + nodeDic[nonprotectedNode[i]] + ','
                    else:
                        pinProtectedInit = pinProtectedInit + nodeDic[nonprotectedNode[i]]
            if len(protectedNode) > 0:
                for i in range(0, len(protectedNode),1):
                    if i != len(protectedNode)-1: 
                        pinInit = pinInit + nodeDic[protectedNode[i]] + ','
                    else:
                        pinInit = pinInit + nodeDic[protectedNode[i]]
        pinInit = pinInit + ';'
        pinProtectedInit = pinProtectedInit + ';'
        #print "Node---->",node
        #print "nodeDic----->",nodeDic
        #print "PinInit----->",pinInit
        #print "pinProtectedinit--->",pinProtectedInit
        return node, nodeDic, pinInit, pinProtectedInit
    
    
    def connectInfo(self,compInfo, node, nodeDic, numNodesSub,subcktName):
        """
        Make node connections in the modelica netlist
        """
        connInfo = []
        print "compinfo-------->",compInfo
        sourcesInfo = self.separateSource(compInfo)
        for eachline in compInfo:
            words = eachline.split()
            
            if eachline[0]=='r' or eachline[0]=='R' or eachline[0]=='c' or eachline[0]=='C' or eachline[0]=='d' or eachline[0]=='D' \
            or eachline[0]=='l' or eachline[0]=='L' or eachline[0]=='v' or eachline[0]=='V' or eachline[0]=='i' or eachline[0]=='I':
                conn = 'connect(' + words[0] + '.p,' + nodeDic[words[1]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.n,' + nodeDic[words[2]] + ');'
                connInfo.append(conn)
            elif eachline[0]=='q' or eachline[0]=='Q':
                print "Node Dict------>",nodeDic
                conn = 'connect(' + words[0] + '.C,' + nodeDic[words[1]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.B,' + nodeDic[words[2]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.E,' + nodeDic[words[3]] + ');'
                connInfo.append(conn)
            elif eachline[0]=='m' or eachline[0]=='M':
                conn = 'connect(' + words[0] + '.D,' + nodeDic[words[1]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.G,' + nodeDic[words[2]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.S,' + nodeDic[words[3]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.B,' + nodeDic[words[4]] + ');'
                connInfo.append(conn)
            elif eachline[0] in ['f','h','F','H']:
                vsource = words[3]
                sourceNodes = sourcesInfo[vsource]
                sourceNodes = sourceNodes.split()
                conn = 'connect(' + words[0] + '.p1,'+ nodeDic[sourceNodes[0]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.n1,'+ nodeDic[sourceNodes[1]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.p2,'+ nodeDic[words[1]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.n2,'+ nodeDic[words[2]] + ');'
                connInfo.append(conn)
            elif eachline[0] in ['g','e','G','E']:
                conn = 'connect(' + words[0] + '.p1,'+ nodeDic[words[3]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.n1,'+ nodeDic[words[4]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.p2,'+ nodeDic[words[1]] + ');'
                connInfo.append(conn)
                conn = 'connect(' + words[0] + '.n2,'+ nodeDic[words[2]] + ');'
                connInfo.append(conn)
            elif eachline[0]=='x' or eachline[0]=='X':
                templine = eachline.split()
                temp = templine[0].split('x')
                index = temp[1]
                for i in range(0,len(templine),1):
                    if templine[i] in subcktName:   #Ask Manas Added subcktName in function Call
                        subname = templine[i]
                nodeNumInfo = self.getSubInterface(subname, numNodesSub)
                for i in range(0, numNodesSub[subname], 1):
                    #conn = 'connect(' + subname + '_instance' + index + '.' + nodeDic[nodeNumInfo[i]] + ',' + nodeDic[words[i+1]] + ');'
                    conn = 'connect(' + subname + '_instance' + index + '.' + 'n'+ nodeNumInfo[i] + ',' + nodeDic[words[i+1]] + ');'
                    connInfo.append(conn)
            else:
                continue
        if '0' in node:
            conn = 'connect(g.p,n0);'
            connInfo.append(conn)
        elif 'gnd' in node:
            conn = 'connect(g.p,ngnd);'
            connInfo.append(conn)
         
        return connInfo
    
    
    def procesSubckt(self,subcktName,numNodesSub,dir_name):
        
        #Process the subcircuit file .sub in the project folder
        
        #subcktDic = {}
        subOptionInfo = []
        subSchemInfo = []
        subModel = []
        subModelInfo = {}
        subsubName = [] 
        subParamInfo = []
        #subinbuiltmodelName = []
        #subinbuiltmodelInfo = {}
        nodeSubInterface = []
        nodeSub = []
        nodeDicSub = {}
        pinInitsub = []
        connSubInfo = []
        print "subcktName------------------>",subcktName
        if len(subcktName) > 0:
            for eachsub in subcktName:
                filename = eachsub + '.sub'
                data = self.readNetlist(filename)
                print "Data-------------------->",data
                subOptionInfo, subSchemInfo = self.separateNetlistInfo(data)
                print "SubOptionInfo------------------->",subOptionInfo
                print "SubSchemInfo-------------------->",subSchemInfo
                if len(subOptionInfo) > 0:
                    newline = subOptionInfo[0]
                    subInitLine = newline
                    newline = newline.split('.subckt')       
                    intLine = newline[1].split()
                    for i in range(0,len(intLine),1):
                        nodeSubInterface.append(intLine[i])
                    
                subModel, subModelInfo, subsubName, subParamInfo,transInfo = self.addModel(subOptionInfo)
                print "Sub Model------------------------------------>",subModel
                print "SubModelInfo---------------------------------->",subModelInfo
                print "subsubName------------------------------------->",subsubName
                print "subParamInfo----------------------------------->",subParamInfo
                print "transInfo----------------------------------->",transInfo
                IfMOSsub = '0'
                for eachline in subSchemInfo:
                    #words = eachline.split()
                    if eachline[0] == 'm':
                        IfMOSsub = '1'
                        break
                subsubOptionInfo = []
                subsubSchemInfo = []
                if len(subsubName) > 0:
                    #subsubOptionInfo = []
                    #subsubSchemInfo = []
                    for eachsub in subsubName:
                        filename_stemp = eachsub + '.sub'
                        data = self.readNetlist(filename_stemp)
                        subsubOptionInfo, subsubSchemInfo = self.separateNetlistInfo(data)
                        for eachline in subsubSchemInfo:
                            #words = eachline.split()
                            if eachline[0] == 'm':
                                IfMOSsub = '1'
                                break
                print "subsubOptionInfo-------------------------->",subsubOptionInfo
                print "subsubSchemInfo-------------------------->",subsubSchemInfo
                
                modelicaSubParam =  self.processParam(subParamInfo)
                print "modelicaSubParam------------------->",modelicaSubParam
                nodeSub, nodeDicSub, pinInitSub, pinProtectedInitSub = self.nodeSeparate(subSchemInfo, '1', eachsub, subsubName,numNodesSub)
                print "NodeSub------------------------->",nodeSub
                print "NodeDicSub-------------------------->",nodeDicSub
                print "PinInitSub-------------------------->",pinInitSub
                print "PinProtectedInitSub------------------->",pinProtectedInitSub
                modelicaSubCompInit, numNodesSubsub = self.compInit(subSchemInfo, nodeSub, subModelInfo, subsubName,dir_name,transInfo)
                print "modelicaSubCompInit--------------------->",modelicaSubCompInit
                print "numNodesSubsub-------------------------->",numNodesSubsub
                modelicaSubParamNew = self.getSubParamLine(eachsub, numNodesSub, modelicaSubParam,dir_name)     ###Ask Manas
                print "modelicaSubParamNew----------------->",modelicaSubParamNew
                connSubInfo = self.connectInfo(subSchemInfo, nodeSub, nodeDicSub, numNodesSubsub,subcktName)
                newname = filename.split('.')
                newfilename = newname[0]
                outfilename = newfilename+ ".mo"
                out = open(outfilename,"w")
                out.writelines('model ' + os.path.basename(newfilename))
                out.writelines('\n')
                if IfMOSsub == '0':
                    out.writelines('import Modelica.Electrical.*;')
                elif IfMOSsub == '1':
                    out.writelines('import BondLib.Electrical.*;')
                out.writelines('\n') 
                for eachline in modelicaSubParamNew:
                    if len(subParamInfo) == 0:
                        continue
                    else:
                        out.writelines(eachline) 
                        out.writelines('\n')
                for eachline in modelicaSubCompInit:
                    if len(subSchemInfo) == 0:
                        continue
                    else:
                        out.writelines(eachline)
                        out.writelines('\n')
                        
                out.writelines(pinProtectedInitSub)
                out.writelines('\n')
                if pinInitSub != 'Modelica.Electrical.Analog.Interfaces.Pin ;':
                    out.writelines('protected')
                    out.writelines('\n')
                    out.writelines(pinInitSub)
                    out.writelines('\n')
                out.writelines('equation')
                out.writelines('\n')
                for eachline in connSubInfo:
                    if len(connSubInfo) == 0:
                        continue
                    else:
                        out.writelines(eachline)
                        out.writelines('\n')
                out.writelines('end '+ os.path.basename(newfilename) + ';')
                out.writelines('\n')
                out.close()
            
        return data, subOptionInfo, subSchemInfo, subModel, subModelInfo, subsubName, \
            subParamInfo, modelicaSubCompInit, modelicaSubParam, nodeSubInterface, nodeSub, nodeDicSub, pinInitSub, connSubInfo         
                                 
    

def main(args):
    """
    It is main function of module Ngspice to Modelica converter
    """
    if len(sys.argv) == 2:
        filename = sys.argv[1]
    else:
        print "USAGE:"
        print "python NgspicetoModelica.py <filename>"
        sys.exit()
        
    dir_name = os.path.dirname(os.path.realpath(filename))
    file_basename = os.path.basename(filename)
    
    obj_NgMoConverter = NgMoConverter()
    
    #Getting all the require information
    lines = obj_NgMoConverter.readNetlist(filename)
    #print "Complete Lines of Ngspice netlist :lines ---------------->",lines
    optionInfo, schematicInfo = obj_NgMoConverter.separateNetlistInfo(lines)
    #print "All option details like analysis,subckt,.ic,.model  : OptionInfo------------------->",optionInfo
    #print "Schematic connection info :schematicInfo",schematicInfo
    modelName, modelInfo, subcktName, paramInfo,transInfo = obj_NgMoConverter.addModel(optionInfo)
    print "Name of Model : modelName-------------------->",modelName
    print "Model Information :modelInfo--------------------->",modelInfo
    #print "Subcircuit Name :subcktName------------------------>",subcktName
    #print "Parameter Information :paramInfo---------------------->",paramInfo
        
    
    modelicaParamInit = obj_NgMoConverter.processParam(paramInfo)
    #print "Make modelicaParamInit from paramInfo  :processParamInit------------->",modelicaParamInit 
    compInfo, plotInfo = obj_NgMoConverter.separatePlot(schematicInfo)
    print "Info like run etc  : CompInfo----------------->",compInfo
    #print "Plot info like plot,print etc :plotInfo",plotInfo
    IfMOS = '0'
    
    for eachline in compInfo:
        words = eachline.split()
        if eachline[0] == 'm':
            IfMOS = '1'
            break
    subOptionInfo = []
    subSchemInfo = []
    if len(subcktName) > 0:
        #subOptionInfo = []
        #subSchemInfo = []
        for eachsub in subcktName:
            filename_temp = eachsub + '.sub'
            data = obj_NgMoConverter.readNetlist(filename_temp)
            subOptionInfo, subSchemInfo = obj_NgMoConverter.separateNetlistInfo(data)
            for eachline in subSchemInfo:
                words = eachline.split()
                if eachline[0] == 'm':
                    IfMOS = '1'
                    break
    #print "Subcircuit OptionInfo : subOptionInfo------------------->",subOptionInfo
    #print "Subcircuit Schematic Info :subSchemInfo-------------------->",subSchemInfo
                
    node, nodeDic, pinInit, pinProtectedInit = obj_NgMoConverter.nodeSeparate(compInfo, '0', [], subcktName,[])
    print "All nodes in the netlist :node---------------->",node
    print "NodeDic which will be used for modelica : nodeDic------------->",nodeDic
    #print "PinInit-------------->",pinInit
    #print "pinProtectedInit----------->",pinProtectedInit
    
    modelicaCompInit, numNodesSub  = obj_NgMoConverter.compInit(compInfo,node, modelInfo, subcktName,dir_name,transInfo)
    print "ModelicaComponents : modelicaCompInit----------->",modelicaCompInit
    print "SubcktNumNodes : numNodesSub---------------->",numNodesSub
    
    connInfo = obj_NgMoConverter.connectInfo(compInfo, node, nodeDic, numNodesSub,subcktName)
    
    #print "ConnInfo------------------>",connInfo
    
    
    ###After Sub Ckt Func
    if len(subcktName) > 0:
        data, subOptionInfo, subSchemInfo, subModel, subModelInfo, subsubName,subParamInfo, modelicaSubCompInit, modelicaSubParam,\
        nodeSubInterface,nodeSub, nodeDicSub, pinInitSub, connSubInfo = obj_NgMoConverter.procesSubckt(subcktName,numNodesSub,dir_name) #Adding 'numNodesSub' by Fahim
    
    #Creating Final Output file
    newfile = filename.split('.')
    newfilename = newfile[0]
    outfile = newfilename + ".mo"
    out = open(outfile,"w")
    out.writelines('model ' + os.path.basename(newfilename))
    out.writelines('\n')
    if IfMOS == '0':
        out.writelines('import Modelica.Electrical.*;')
    elif IfMOS == '1':
        out.writelines('import BondLib.Electrical.*;')
        #out.writelines('import Modelica.Electrical.*;')
    out.writelines('\n')
    
    for eachline in modelicaParamInit:
        if len(paramInfo) == 0:
            continue
        else:
            out.writelines(eachline)
            out.writelines('\n')
    for eachline in modelicaCompInit:
        if len(compInfo) == 0:
            continue
        else:
            out.writelines(eachline)
            out.writelines('\n')
    
    out.writelines('protected')
    out.writelines('\n')
    out.writelines(pinInit)
    out.writelines('\n')
    out.writelines('equation')
    out.writelines('\n')
    
    for eachline in connInfo:
        if len(connInfo) == 0:
            continue
        else:
            out.writelines(eachline)
            out.writelines('\n')
            
    out.writelines('end '+ os.path.basename(newfilename) + ';')
    out.writelines('\n')


    out.close()
    

# Call main function
if __name__ == '__main__':
    main(sys.argv)
