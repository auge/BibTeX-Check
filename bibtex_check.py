#!/usr/bin/env python3

"""
BibTeX check on missing fields and consistent name conventions (no BibTeX validator),
especially developed for requirements in Computer Science.
"""
import string
import re
import sys
from optparse import OptionParser
from datetime import datetime
import dateutil.parser
from unidecode import unidecode


__author__ = "Benjamin Steinwender"
__version__ = "0.6.0"
__credits__ = ["BibLaTeX Check by Pez Cuckow", "BibTex Check 0.2.0 by Fabian Beck"]
__license__ = "MIT"

####################################################################
# Properties (please change according to your needs)
####################################################################

# links
citeulikeUsername = ""  # if no username is profided, no CiteULike links appear
citeulikeHref = "http://www.citeulike.org/user/" + citeulikeUsername + "/article/"
scholarHref = "http://scholar.google.de/scholar?hl=en&q="
googleHref = "https://duckduckgo.com/?q="
dblpHref = "http://dblp.org/search/index.php#query="

# fields that are required for a specific type of entry
requiredFields = {
    "article": ["author", "title", "journal", "year", "volume"],
    "book": ["author/editor", "title", "publisher", "year"],
    "booklet": ["author/editor", "title", "year", "howpublished"],
    "conference": "inproceedings",
    "inbook": ["author/editor", "title", "chapter/pages", "publisher", "year"],
    "incollection": ["author", "title", "booktitle", "publisher", "year"],
    "inproceedings": ["author", "title", "booktitle", "year"],
    "manual": ["title", "year"],
    "mastersthesis": ["author", "title", "school", "year"],
    "misc": ["author/organization", "title", "year"],
    "phdthesis": ["author", "title", "school", "year"],
    "proceedings": ["title", "year"],
    "techreport": ["author", "title", "institution", "year"],
    "unpublished": ["author", "title", "note", "year"],

    "electronic": ["author/organization", "title", "url", "year"],
    "standard": ["title", "organization/institution"],
    "patent": ["nationality", "number", "year/yearfiled"],
}

####################################################################


#####
print("INFO: Python version " + str(sys.version_info[0]) + "." + str(sys.version_info[1]) + "." + str(sys.version_info[2]))

# Parse options
parser = OptionParser()

parser.add_option("-b", "--bib", dest="bibFile",
                  help="Bib File", metavar="input.bib", default="input.bib")
parser.add_option("-a", "--aux", dest="auxFile",
                  help="Aux File", metavar="input.aux", default="input.aux")
parser.add_option("-o", "--output", dest="htmlOutput",
                  help="HTML Output File", metavar="output.html")
parser.add_option("-c", "--config", dest="config",
                  help="Config file", metavar="config.json5")
parser.add_option("-v", "--view", dest="view", action="store_true",
                  help="Open in Browser")
parser.add_option("-N", "--no-console", dest="no_console", action="store_true",
                  help="Do not print problems to console")

(options, args) = parser.parse_args()

auxFile = options.auxFile
bibFile = options.bibFile
htmlOutput = options.htmlOutput
configFile = options.config
view = options.view
toconsole = not options.no_console

# Find used referenced IDs only
used_cits = set()
try:
    fInAux = open(auxFile, 'r', encoding="utf8")
    for line in fInAux:
        if line.startswith("\\citation"):
            citations = line.split("{")[1].rstrip("} \n").split(", ")
            for cit in citations:
                if cit != "":
                    used_cits.add(cit)
    fInAux.close()
except IOError as e:
    print("INFO: Aux file '" + auxFile +
          "' doesn't exist -> not restricting entries")

try:
    fIn = open(bibFile, 'r', encoding="utf8")
except IOError as e:
    print("ERROR: Input bib file '" + bibFile +
          "' doesn't exist or is not readable")
    sys.exit(-1)

# Load config file
if configFile:
    try:
        import json5 as json
    except ImportError:
        print("INFO: json5 not installed, trying to use json")
        import json
    with open(configFile) as config:
        data = json.load(config)
    requiredFields = data["requiredFields"]

# Go through and check all references
completeEntry = ""
currentId = ""
citations = []
currentType = ""
currentArticleId = ""
currentTitle = ""
fields = []
problems = []
subproblems = []

counterMissingFields = 0
counterFlawedNames = 0
counterWrongTypes = 0
counterNonUniqueId = 0

removePunctuationMap = dict((ord(char), None) for char in string.punctuation)

lineNo = 0
for line in fIn:
    lineNo += 1
    line = line.strip("\n")
    if line.startswith("@"):
        # bib entry start
        if currentId in used_cits or not used_cits:
            if currentType in requiredFields:
                # resolve type
                while isinstance(requiredFields[currentType], str):
                    currentType = requiredFields[currentType]
                for field in requiredFields[currentType]:
                    # split alternative field combinations
                    # field = "author/editor"; fields might be [author, ...] or [editor, ...]
                    if not any(f in fields for f in field.split("/")):
                        subproblems.append(f"{currentType}: missing field '{field}'")
                        counterMissingFields += 1
            else:
                if currentType and currentType != "comment":
                    print(f"WARNING: Ignoring unspecified entry type {currentType}")
        else:
            subproblems = []

        # check if url is given, but no urldate
        if "url" in fields and "urldate" not in fields:
            subproblems.append("missing field 'urldate' when 'url' is given")
            counterMissingFields += 1

        # check if both url and doi are given
        if "url" in fields and "doi" in fields:
            subproblems.append("both 'url' and 'doi' given - only one recommended")
            counterFlawedNames += 1

        if currentId in used_cits or not used_cits:
            cleanedTitle = currentTitle.translate(removePunctuationMap)
            problem = "<div id='" + currentId + "' class='problem severe" + str(len(subproblems)) + "'>"
            problem += "<h2>" + currentId + " (" + currentType + ")</h2> "
            problem += "<div class='links'>"
            if citeulikeUsername:
                problem += "<a href='" + citeulikeHref + currentArticleId + "' target='_blank'>CiteULike</a>"
            problem += " | <a href='" + scholarHref + cleanedTitle + "' target='_blank'>Scholar</a>"
            problem += " | <a href='" + googleHref + cleanedTitle + "' target='_blank'>Google</a>"
            problem += " | <a href='" + dblpHref + cleanedTitle + "' target='_blank'>DBLP</a>"
            problem += "</div>"
            problem += "<div class='reference'>" + currentTitle + "</div>"
            problem += "<ul>"
            for subproblem in subproblems:
                problem += "<li>" + subproblem + "</li>"
                if toconsole:
                    try:
                        print("PROBLEM: " + currentId + " - " + subproblem)
                    except UnicodeEncodeError:
                        print(("PROBLEM: " + currentId + " - " + subproblem).encode('utf-8'))
            problem += "</ul>"
            problem += "<form class='problem_control'><label>checked</label><input type='checkbox' class='checked'/></form>"
            problem += "<div class='bibtex_toggle'>Current BibTeX Entry</div>"
            problem += "<div class='bibtex'>" + completeEntry + "</div>"
            problem += "</div>"
            problems.append(problem)
        fields = []
        subproblems = []
        currentId = line.split("{")[1].rstrip(",\n").lower().strip()
        if currentId in citations:
            subproblems.append("non-unique id: '" + currentId + "'")
            counterNonUniqueId += 1
        else:
            citations.append(currentId)
        currentType = line.split("{")[0].strip("@ ").lower()
        completeEntry = line + "<br />"
        if currentId == '':
            subproblems.append(f"line {lineNo}: missing bibkey for {currentType} found")
            counterFlawedNames += 1
    else:
        # bib entry contents
        if line != "":
            completeEntry += line + "<br />"
        if currentId in used_cits or not used_cits:
            if "=" in line:
                # bibtex is case sensitive
                field = line.split("=")[0].strip().lower()
                fields.append(field)
                value = line.split("=")[1].strip("{} ,\n")
                if value == "null":
                    subproblems.append(f"value of field {field} is null")
                    counterMissingFields += 1
                if field == "author":
                    # check correct author format
                    authors = value.split(" and ")
                    for a in authors:
                        if a.count(',') > 1:
                            subproblems.append("flawed name: author with more than 1 comma found '" + value + "'")
                            counterFlawedNames += 1
                    currentAuthor = filter(lambda x: not (x in "\\\"{}"), authors[0])
                    # check whether author name has curly braces
                    if "{" in value or "}" in value:
                        subproblems.append("authors field has curly braces {} - not needed")
                        counterFlawedNames += 1
                    # check whether author name is part of bibkey
                    firstAuthor = authors[0]
                    if "," in firstAuthor:
                        firstAuthorLastname = firstAuthor.split(",")[0].strip("{} ,\n")
                    else:
                        firstAuthorLastname = firstAuthor.split(" ")[-1].strip("{} ,\n")
                    firstAuthorLastname = firstAuthorLastname.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                    firstAuthorLastname = unidecode(firstAuthorLastname).lower().replace(" ", "").replace(".", "").replace("'", "")
                    if firstAuthorLastname not in currentId and firstAuthorLastname.replace("-", "") not in currentId:
                        subproblems.append(f"first authors last name '{firstAuthorLastname}' not part of bib-key")
                        counterFlawedNames += 1
                if field == "year":
                    # check year is 4-digit and in valid range
                    minyear = 1900
                    maxyear = int(datetime.now().year) + 1
                    try:
                        if not minyear < int(value) <= maxyear:
                            subproblems.append(f"year must be in range of ({minyear}, {maxyear})")
                            counterFlawedNames += 1
                    except ValueError as e:
                        subproblems.append(f"failed to parse year '{value}'")
                        counterFlawedNames += 1
                    # check year is contained in bib-key
                    if value not in currentId:
                        subproblems.append("year is not part of bib-key")
                        counterFlawedNames += 1
                if field == "pages":
                    if value.startswith("1--"):
                        subproblems.append(f"pages '{value}' is most likey not correct: check that your reference really starts on page 1")
                if field == "urldate":
                    # check urldate is iso-formatted
                    try:
                        urldate = dateutil.parser.parse(value)
                    except ValueError as e:
                        subproblems.append(f"urldate '{value}' is not formatted according to ISO 8601")
                        counterFlawedNames += 1
                if field == "citeulike-article-id":
                    currentArticleId = value
                if field == "title":
                    currentTitle = re.sub(r'[}{]', r'', value)
                if field == "doi":
                    # must not contain http
                    if value.startswith("http"):
                        subproblems.append("DOI '" + value + "' must not start with http - only the numeric part is sufficient")
                        counterDocumentLinkErrors += 1

                ###############################################################
                # Checks (please (de)activate/extend to your needs)
                ###############################################################

                # check if type 'proceedings' might be 'inproceedings'
                if currentType == "proceedings" and field == "pages":
                    subproblems.append("wrong type: maybe should be 'inproceedings' because entry has page numbers")
                    counterWrongTypes += 1

                # check if abbreviations are used in journal titles
                if currentType == "article" and field == "journal":
                    if "." in line:
                        subproblems.append("flawed name: abbreviated journal title '" + value + "'")
                        counterFlawedNames += 1

            ###############################################################

fIn.close()


problemCount = counterMissingFields + counterFlawedNames + counterWrongTypes + counterNonUniqueId

# Write out our HTML file
if htmlOutput:
    html = open(htmlOutput, 'w', encoding="utf8")
    html.write("""<!doctype html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<title>BibTeX Check</title>
<style>
body {
    font-family: Calibri, Arial, Sans;
    padding: 10px;
    width: 1030px;
    margin: 10px auto;
    border-top: 1px solid black;
}

#title {
    width: 720px;
    border-bottom: 1px solid black;
}

#title h1 {
    margin: 10px 0px;
}

#title h1 a {
    color: black;
    text-decoration: none;
}

#control {
    clear: both;
}

#search {
    float: left;
}

#search input {
    width: 300px;
    font-size: 14pt;
}

#mode {
    text-align: right;
}

#mode label:first-child {
    font-weight: bold;
}

#mode input {
    margin-left: 20px;
}

.info {
    margin-top: 10px;
    padding: 10px;
    background: #FAFADD;
    width: 250px;
    float: right;
    box-shadow: 1px 1px 1px 1px #ccc;
    clear: both;
}

.info h2 {
    font-size: 12pt;
    padding: 0px;
    margin: 0px;
}

.problem {
    margin-top: 10px;
    margin-bottom: 10px;
    padding: 10px;
    background: #FFBBAA;
    counter-increment: problem;
    width: 700px;
    border: 1px solid #993333;
    border-left: 5px solid #993333;
    box-shadow: 1px 1px 1px 1px #ccc;
    float: left;
}

.active {
    box-shadow: 5px 5px 3px 3px #ccc;
    position: relative;
    top: -2px;
}

.severe0 {
    background: #FAFAFA;
    border: 1px solid black;
    border-left: 5px solid black;
}

.severe1 {
    background: #FFEEDD;
}

.severe2 {
    background: #FFDDCC;
}

.severe3 {
    background: #FFCCBB;
}

.problem_checked {
    border: 1px solid #339933;
    border-left: 5px solid #339933;
}

.problem h2:before {
    content: counter(problem) ". "; color: gray;
}

.problem h2 {
    font-size: 12pt;
    padding: 0px;
    margin: 0px;
}

.problem .links {
    float: right;
    position:relative;
    top: -22px;
}

.problem .links a {
    color: #3333CC;
}

.problem .links a:visited {
    color: #666666;
}

.problem .reference {
    clear: both;
    font-size: 9pt;
    margin-left: 20px;
    font-style:italic;
    font-weight:bold;
}

.problem ul {
    clear: both;
}

.problem .problem_control {
    float: right;
    margin: 0px;
    padding: 0px;
}

.problem .bibtex_toggle{
    text-decoration: underline;
    font-size: 9pt;
    cursor: pointer;
    padding-top: 5px;
}

.problem .bibtex {
    margin-top: 5px;
    font-family: Monospace;
    font-size: 8pt;
    display: none;
    border: 1px solid black;
    background-color: #FFFFFF;
    padding: 5px;
}
</style>
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.5/jquery.min.js"></script>
<script>

function isInProblemMode() {
    return $('#mode_problems:checked').val() == 'problems'
}

function update() {
    $('.problem').hide();
    $('.problem[id*='+$('#search input').val()+']').show();
    $('.problem .checked').each(function () {
        if ($(this).attr('checked')) {
            $(this).parents('.problem').addClass('problem_checked');
        } else {
            $(this).parents('.problem').removeClass('problem_checked');
        }
    });
    if (isInProblemMode()) {
        $('.severe0').hide();
        $('.problem_checked').hide();
    }
}

$(document).ready(function(){

    $(".bibtex_toggle").click(function(event){
        event.preventDefault();
        $(this).next().slideToggle();
    });

    $('#search input').live('input', function() {
        update();
    });

    $('#mode input').change(function() {
        update();
    });

    $("#uncheck_button").click(function(){
        $('.problem .checked').attr('checked',false);
        localStorage.clear();
        update();
    });

    $('.problem a').mousedown(function(event) {
        $('.problem').removeClass('active');
        $(this).parents('.problem').addClass('active');
    });

    $('.problem .checked').change(function(event) {
        var problem = $(this).parents('.problem');
        problem.toggleClass('problem_checked');
        var checked = problem.hasClass('problem_checked');
        localStorage.setItem(problem.attr('id'),checked);
        if (checked && isInProblemMode()) {
            problem.slideUp();
        }
    });

    $('.problem .checked').each(function () {
        $(this).attr('checked',localStorage.getItem($(this).parents('.problem').attr('id'))=='true');
    });
    update();
});

</script>
</head>
<body>
<div id="title">
<h1><a href='http://github.com/auge/BibTeX-Check'>BibTeX Check</a></h1>
<div id="control">
<form id="search"><input placeholder="search entry ID ..."/></form>
<form id="mode">
<label>show entries:</label>
<input type = "radio"
                 name = "mode"
                 id = "mode_problems"
                 value = "problems"
                 checked = "checked" />
          <label for = "mode_problems">problems</label>
          <input type = "radio"
                 name = "mode"
                 id = "mode_all"
                 value = "all" />
          <label for = "mode_all">all</label>
<input type="button" value="uncheck all" id="uncheck_button"></button>
</form>
<br style="clear: both; " />
</div>
</div>
""")
    html.write("<div class='info'><h2>Info</h2><ul>")
    html.write("<li>bib file: " + bibFile + "</li>")
    html.write("<li>aux file: " + auxFile + "</li>")
    html.write("<li># entries: " + str(len(problems)) + "</li>")
    html.write("<li># problems: " + str(problemCount) + "</li><ul>")
    html.write("<li># missing fields: " + str(counterMissingFields) + "</li>")
    html.write("<li># flawed names: " + str(counterFlawedNames) + "</li>")
    html.write("<li># wrong types: " + str(counterWrongTypes) + "</li>")
    html.write("<li># non-unique id: " + str(counterNonUniqueId) + "</li>")
    html.write("</ul></ul></div>")

    problems.sort()
    for problem in problems:
        html.write(problem)
    html.write("</body></html>")
    html.close()

    if view:
        import webbrowser
        webbrowser.open(html.name)

    print(f"SUCCESS: Report {htmlOutput} has been generated")

if problemCount > 0:
    print(f"PROBLEM: Found {problemCount} problems.")
    sys.exit(-1)

print(f"INFO: done.")
