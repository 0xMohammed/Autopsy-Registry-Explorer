import inspect
import os
import shutil
import ntpath
import subprocess
import csv
from java.io import File
from java.lang import Class
from java.lang import System
from java.sql  import DriverManager, SQLException
from java.util.logging import Level
from java.util import Arrays
from org.sleuthkit.datamodel import SleuthkitCase
from org.sleuthkit.datamodel import AbstractFile
from org.sleuthkit.datamodel import ReadContentInputStream
from org.sleuthkit.datamodel import BlackboardArtifact
from org.sleuthkit.datamodel import BlackboardAttribute
from org.sleuthkit.datamodel import Blackboard
from org.sleuthkit.datamodel import TskData
from org.sleuthkit.autopsy.ingest import IngestModule
from org.sleuthkit.autopsy.ingest.IngestModule import IngestModuleException
from org.sleuthkit.autopsy.ingest import DataSourceIngestModule
from org.sleuthkit.autopsy.ingest import IngestModuleFactoryAdapter
from org.sleuthkit.autopsy.ingest import IngestModuleIngestJobSettings
from org.sleuthkit.autopsy.ingest import IngestModuleIngestJobSettingsPanel
from org.sleuthkit.autopsy.ingest import IngestMessage
from org.sleuthkit.autopsy.ingest import IngestServices
from org.sleuthkit.autopsy.ingest import ModuleDataEvent
from org.sleuthkit.autopsy.coreutils import Logger
from org.sleuthkit.autopsy.coreutils import PlatformUtil
from org.sleuthkit.autopsy.casemodule import Case
from org.sleuthkit.autopsy.casemodule.services import Services
from org.sleuthkit.autopsy.casemodule.services import FileManager
from org.sleuthkit.autopsy.datamodel import ContentUtils
from org.sleuthkit.autopsy.modules.interestingitems import FilesSetsManager
class RegistryExplorerIngestModuleFactory(IngestModuleFactoryAdapter):
    def __init__(self):
        self.settings = None
    moduleName = "RegistyExplorer Module"
    def getModuleDisplayName(self):
        return self.moduleName
    def getModuleDescription(self):
        return "Extract Keys To Look For Interesting Items"
    def getModuleVersionNumber(self):
        return "0.1 Beta"
    def hasIngestJobSettingsPanel(self):
        return False
    def isDataSourceIngestModuleFactory(self):
        return True
    def createDataSourceIngestModule(self, ingestOptions):
        return RegistryExplorerIngestModule(self.settings)
class RegistryExplorerIngestModule(DataSourceIngestModule):
    _logger = Logger.getLogger(RegistryExplorerIngestModuleFactory.moduleName)
    def log(self, level, msg):
        self._logger.logp(level, self.__class__.__name__, inspect.stack()[1][3], msg)
    def __init__(self, settings):
        self.context = None
    def startUp(self, context):
        self.context = context
        if PlatformUtil.isWindowsOS():
            self.regparser_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regparser.exe")
            self.rla_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rla.exe")
            if not os.path.exists(self.regparser_exe) or not os.path.exists(self.rla_exe):
                raise IngestModuleException("EXE was not found in module folder")
        else:
            raise IngestModuleException("This module is for Windows OS only")
    def process(self, dataSource, progressBar):
        progressBar.switchToIndeterminate()
        filesToExtract = ("NTUSER.DAT", "SOFTWARE", "UsrClass.dat", "SAM", "SYSTEM", "SECURITY")
        logToExtract = ("%NTUSER%", "%SOFTWARE%", "%UsrClass%", "%SAM%", "%SYSTEM%", "%SECURITY%")
        dir_search = ('/WINDOWS/SYSTEM32/CONFIG/','/Users/', '/Windows/ServiceProfiles')
        tempDir = os.path.join(Case.getCurrentCase().getTempDirectory(), "RegistryExplorer")
        self.log(Level.INFO, "create Directory " + tempDir)
        try:
            os.mkdir(tempDir)
        except Exception as e:
            self.log(Level.INFO, "RegistryExplorer Directory already exists " + tempDir)
        skCase = Case.getCurrentCase().getSleuthkitCase()
        blackboard = Case.getCurrentCase().getSleuthkitCase().getBlackboard()
        fileManager = Case.getCurrentCase().getServices().getFileManager()
        registry_hives = []
        softwarehive = ntuserhive = usrclasshive = samhive = systemhive = "na"
        for fileName in filesToExtract:
            for dirName in dir_search:
                files = fileManager.findFiles(dataSource, fileName, dirName)
                for file in files:
                    if self.context.isJobCancelled():
                        return IngestModule.ProcessResult.OK
                    if ((file.getName() == 'SOFTWARE') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-softprnt'] = file.getParentPath()
                    elif ((file.getName() == 'NTUSER.DAT') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-ntusrprnt'] = file.getParentPath()
                    elif ((file.getName() == 'UsrClass.dat') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-usrclsprnt'] = file.getParentPath()
                    elif ((file.getName() == 'SAM') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-samprnt'] = file.getParentPath()
                    elif ((file.getName() == 'SYSTEM') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-systemprnt'] = file.getParentPath()
        for logName in logToExtract:
            for dirName in dir_search:
                files = fileManager.findFiles(dataSource, logName, dirName)
                for file in files:
                    if file.getNameExtension().upper() == 'LOG' \
                    or file.getNameExtension().upper() == 'LOG1' \
                    or file.getNameExtension().upper() == 'LOG2' \
                    or file.getNameExtension().upper() == 'DLL' \
                    or file.getNameExtension().upper() == 'EXE' \
                    or file.getNameExtension().upper() == 'CSV' \
                    or file.getNameExtension().upper() == 'BLF' \
                    or file.getNameExtension().upper() == 'REGTRANS-MS' \
                    or file.getNameExtension().upper() == 'TXT' \
                    or file.getNameExtension().upper() == 'INI':
                        if file.getSize > 0:
                            for extracted_files in registry_hives:
                                try:
                                    if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-usrclsprnt'] and 'usrclass' in file.getName().lower():
                                        ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                except KeyError:
                                    try:
                                        if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-systemprnt'] and 'system' in file.getName().lower():
                                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                    except KeyError:
                                        try:
                                            if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-samprnt'] and 'sam' in file.getName().lower():
                                                ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                        except KeyError:
                                            try:
                                                if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-ntusrprnt'] and 'ntuser' in file.getName().lower():
                                                    ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                            except KeyError:
                                                try:
                                                    if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-softprnt'] and 'software' in file.getName().lower():
                                                        ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                                except KeyError:
                                                    continue
        if os.listdir(tempDir) == []:
            for fileName in filesToExtract:
                files = fileManager.findFiles(dataSource, fileName)
                for file in files:
                    if self.context.isJobCancelled():
                        return IngestModule.ProcessResult.OK
                    if ((file.getName() == 'SOFTWARE') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-softprnt'] = file.getParentPath()
                    elif ((file.getName() == 'NTUSER.DAT') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-ntusrprnt'] = file.getParentPath()
                    elif ((file.getName() == 'UsrClass.dat') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-usrclsprnt'] = file.getParentPath()
                    elif ((file.getName() == 'SAM') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-samprnt'] = file.getParentPath()
                    elif ((file.getName() == 'SYSTEM') and (file.getSize() > 0)):
                            fileName = str(file.getId()) + "-" + file.getName()
                            registry_hives.append(fileName)
                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, fileName)))
                            globals()[fileName]=file
                            globals()[str(file.getId())+'-systemprnt'] = file.getParentPath()
            for logName in logToExtract:
                    files = fileManager.findFiles(dataSource, logName)
                    for file in files:
                        if file.getNameExtension().upper() == 'LOG' \
                        or file.getNameExtension().upper() == 'LOG1' \
                        or file.getNameExtension().upper() == 'LOG2' \
                        or file.getNameExtension().upper() == 'DLL' \
                        or file.getNameExtension().upper() == 'EXE' \
                        or file.getNameExtension().upper() == 'CSV' \
                        or file.getNameExtension().upper() == 'BLF' \
                        or file.getNameExtension().upper() == 'REGTRANS-MS' \
                        or file.getNameExtension().upper() == 'TXT' \
                        or file.getNameExtension().upper() == 'INI':
                            if file.getSize > 0:
                                for extracted_files in registry_hives:
                                    try:
                                        if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-usrclsprnt'] and 'usrclass' in file.getName().lower():
                                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                    except KeyError:
                                        try:
                                            if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-systemprnt'] and 'system' in file.getName().lower():
                                                ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                        except KeyError:
                                            try:
                                                if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-samprnt'] and 'sam' in file.getName().lower():
                                                    ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                            except KeyError:
                                                try:
                                                    if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-ntusrprnt'] and 'ntuser' in file.getName().lower():
                                                        ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                                except KeyError:
                                                    try:
                                                        if file.getParentPath() == globals()[str(extracted_files.split('-')[0])+'-softprnt'] and 'software' in file.getName().lower():
                                                            ContentUtils.writeToFile(file, File(os.path.join(tempDir, str(extracted_files.split('-')[0])+'-'+file.getName())))
                                                    except KeyError:
                                                        continue
        self.log(Level.INFO,subprocess.Popen([self.rla_exe, '--d', tempDir, '--out', tempDir+'\\..\\'], stdout=subprocess.PIPE).communicate()[0])
        dirty_hives = False
        for file in os.listdir(tempDir):
            if 'LOG' in str(file).upper() \
            or 'LOG1' in str(file).upper() \
            or 'LOG2' in str(file).upper() \
            or 'DLL' in str(file).upper() \
            or 'EXE' in str(file).upper() \
            or 'CSV' in str(file).upper() \
            or 'BLF' in str(file).upper() \
            or 'REGTRANS-MS' in str(file).upper() \
            or 'TXT' in str(file).upper() \
            or 'INI' in str(file).upper():
                dirty_hives = True
                break
        if dirty_hives == True:
            message = IngestMessage.createMessage(IngestMessage.MessageType.DATA,
                "RegistryExplorer", " Some Dirty Hives Found. " )
            IngestServices.getInstance().postMessage(message)
            message = IngestMessage.createMessage(IngestMessage.MessageType.DATA,
                "RegistryExplorer", " Transaction logs have been replayed. " )
            IngestServices.getInstance().postMessage(message)
        for file in os.listdir(tempDir+'\\..\\'):
            try:
                os.rename(tempDir+'\\..\\'+file, tempDir+'\\..\\'+file.split('_')[-1])
            except OSError:
                continue
            if 'software' in str(file).lower():
                registry_hive = os.path.join(tempDir+'\\..\\', file.split('_')[-1])
                self.log(Level.INFO,subprocess.Popen([self.regparser_exe, registry_hive, tempDir, os.path.dirname(os.path.abspath(__file__))], stderr=subprocess.PIPE).communicate()[1])
            elif 'ntuser' in str(file).lower():
                registry_hive = os.path.join(tempDir+'\\..\\', file.split('_')[-1])
                self.log(Level.INFO,subprocess.Popen([self.regparser_exe, registry_hive, tempDir, os.path.dirname(os.path.abspath(__file__))], stderr=subprocess.PIPE).communicate()[1])
            elif 'usrclass' in str(file).lower():
                registry_hive = os.path.join(tempDir+'\\..\\', file.split('_')[-1])
                self.log(Level.INFO,subprocess.Popen([self.regparser_exe, registry_hive, tempDir, os.path.dirname(os.path.abspath(__file__))], stderr=subprocess.PIPE).communicate()[1])
            elif 'sam' in str(file).lower():
                registry_hive = os.path.join(tempDir+'\\..\\', file.split('_')[-1])
                self.log(Level.INFO,subprocess.Popen([self.regparser_exe, registry_hive, tempDir, os.path.dirname(os.path.abspath(__file__))], stderr=subprocess.PIPE).communicate()[1])
            elif 'system' in str(file).lower():
                registry_hive = os.path.join(tempDir+'\\..\\', file.split('_')[-1])
                self.log(Level.INFO,subprocess.Popen([self.regparser_exe, registry_hive, tempDir, os.path.dirname(os.path.abspath(__file__))], stderr=subprocess.PIPE).communicate()[1])
        attributeIdRunKeyName = blackboard.getOrAddAttributeType("TSK_REG_KEY_NAME", BlackboardAttribute.TSK_BLACKBOARD_ATTRIBUTE_VALUE_TYPE.STRING, "Name")
        attributeIdRunKeyValue = blackboard.getOrAddAttributeType("TSK_REG_KEY_VALUE", BlackboardAttribute.TSK_BLACKBOARD_ATTRIBUTE_VALUE_TYPE.STRING, "Value")
        attributeIdRegKeyDesc = blackboard.getOrAddAttributeType("TSK_REG_KEY_DESC", BlackboardAttribute.TSK_BLACKBOARD_ATTRIBUTE_VALUE_TYPE.STRING, "Description")
        attributeIdRegKeyCategory = blackboard.getOrAddAttributeType("TSK_REG_KEY_CATEGORY", BlackboardAttribute.TSK_BLACKBOARD_ATTRIBUTE_VALUE_TYPE.STRING, "Category")
        attributeIdRegKeyPath = blackboard.getOrAddAttributeType("TSK_REG_KEY_PATH", BlackboardAttribute.TSK_BLACKBOARD_ATTRIBUTE_VALUE_TYPE.STRING, "PATH")		
        attributeIdRegHiveType = blackboard.getOrAddAttributeType("TSK_REG_HIVE_TYPE", BlackboardAttribute.TSK_BLACKBOARD_ATTRIBUTE_VALUE_TYPE.STRING, "HiveType")
        moduleName = RegistryExplorerIngestModuleFactory.moduleName
        data = []
        with open(tempDir+'.csv') as csv_file:
            keys = csv.reader(csv_file)
            for registryKey in keys:
                if ','.join(registryKey) in data:
                    continue
                else:
                    data.append(','.join(registryKey))
                    artType = blackboard.getOrAddArtifactType( "TSK_REGISTRY_KEYS_"+registryKey[3], "Windows Registry Keys ("+registryKey[3]+")")
                    registry = globals()[registryKey[5]]
                    art = registry.newArtifact(artType.getTypeID())
                    art.addAttributes(((BlackboardAttribute(attributeIdRunKeyName, moduleName, registryKey[0])), \
                                       (BlackboardAttribute(attributeIdRunKeyValue, moduleName, registryKey[1])), \
                                       (BlackboardAttribute(attributeIdRegKeyDesc, moduleName, registryKey[2])), \
                                       (BlackboardAttribute(attributeIdRegKeyCategory, moduleName, registryKey[3])), \
                                       (BlackboardAttribute(attributeIdRegKeyPath, moduleName, registryKey[4])), \
                                       (BlackboardAttribute(attributeIdRegHiveType, moduleName, registryKey[5]))))
                    blackboard.postArtifact(art, moduleName)
        try:
            shutil.rmtree(tempDir+'\\..\\')		
        except Exception as e:
            self.log(Level.INFO, "removal of directory tree failed" + tempDir)
        message = IngestMessage.createMessage(IngestMessage.MessageType.DATA,
            "RegistryExplorer", " RegistryExplorer Files Have Been Analyzed " )
        IngestServices.getInstance().postMessage(message)
        return IngestModule.ProcessResult.OK
