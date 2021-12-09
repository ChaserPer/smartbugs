from sarif_om import *

from src.output_parser.Parser import Parser
from src.output_parser.SarifHolder import isNotDuplicateRule, parseRule, parseResult, \
    parseArtifact, parseLogicalLocation, isNotDuplicateLogicalLocation


class Osiris(Parser):

    @staticmethod
    def extract_result_line(line):
        line = line.replace("INFO:symExec:	  ", '')
        index_split = line.index(":")
        key = line[:index_split].lower().replace(' ', '_').replace('(', '').replace(')', '').replace('└>_', '').strip()
        value = line[index_split + 1:].strip()
        if "True" == value:
            value = True
        elif "False" == value:
            value = False
        return (key, value)

    def is_success(self) -> bool:
        return "====== Analysis Completed ======" in self.str_output

    def parse(self):
        output = []
        current_contract = None
        current_error = None
        lines = self.str_output.splitlines()
        for line in lines:
            if "INFO:root:Contract" in line:
                if current_contract is not None:
                    output.append(current_contract)
                current_contract = {
                    'errors': []
                }
                (file, contract_name, _) = line.replace("INFO:root:Contract ", '').split(':')
                current_contract['file'] = file
                current_contract['name'] = contract_name
            elif "INFO:symExec:	  " in line and '---' not in line and '======' not in line:
                current_error = None
                (key, value) = Osiris.extract_result_line(line)
                if current_contract is None:
                    current_contract = {
                        'errors': [],
                        'file': None,
                    }

                if key == "evm_code_coverage":
                    current_contract['coverage'] = value
                if value == True:
                    current_error = {
                        'message': key,
                    }
                    current_contract['errors'].append(current_error)
            elif current_contract is not None and current_contract['file'] is not None and current_contract['file'] in line and line.index(
                    current_contract['file']) == 0:
                (file, classname, line, column) = line.split(':')
                current_error['line'] = int(line)
                current_error['column'] = int(column)
                current_error['classname'] = classname
        if current_contract is not None:
            output.append(current_contract)
        return output

    def parseSarif(self, osiris_output_results, file_path_in_repo):
        resultsList = []
        logicalLocationsList = []
        rulesList = []

        for analysis in osiris_output_results["analysis"]:

            for result in analysis["errors"]:
                rule = parseRule(tool="osiris", vulnerability=result["message"])
                result = parseResult(tool="osiris", vulnerability=result["message"], level="warning",
                                     uri=file_path_in_repo, line=result["line"], column=result["column"])

                resultsList.append(result)

                if isNotDuplicateRule(rule, rulesList):
                    rulesList.append(rule)

            logicalLocation = parseLogicalLocation(name=analysis["name"])

            if isNotDuplicateLogicalLocation(logicalLocation, logicalLocationsList):
                logicalLocationsList.append(logicalLocation)

        artifact = parseArtifact(uri=file_path_in_repo)

        tool = Tool(driver=ToolComponent(name="Osiris", version="1.0", rules=rulesList,
                                         information_uri="https://github.com/christoftorres/Osiris",
                                         full_description=MultiformatMessageString(
                                             text="Osiris is an analysis tool to detect integer bugs in Ethereum smart contracts. Osiris is based on Oyente.")))

        run = Run(tool=tool, artifacts=[artifact], logical_locations=logicalLocationsList, results=resultsList)

        return run
