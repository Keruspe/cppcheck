#!/usr/bin/python

import re
import glob

def compileCmd(tok):
    if tok == '%any%':
        return 'true'
    elif tok == '%bool%':
        return 'tok->isBoolean()'
    elif tok == '%char%':
        return '(tok->type()==Token::eChar)'
    elif tok == '%comp%':
        return 'tok->isComparisonOp()'
    elif tok == '%num%':
        return 'tok->isNumber()'
    elif tok == '%op%':
        return 'tok->isOp()'
    elif tok == '%or%':
        return '(tok->str()=="|")'
    elif tok == '%oror%':
        return '(tok->str()=="||")'
    elif tok == '%num%':
        return 'tok->isNumber()'
    elif tok == '%str%':
        return '(tok->type()==Token::eString)'
    elif tok == '%type%':
        return '(tok->isName() && tok->varId()==0U && tok->str() != "delete")'
    elif tok == '%var%':
        return 'tok->isName()'
    elif (len(tok)>2) and (tok[0]=="%"):
        print "unhandled:" + tok
    return '(tok->str()=="'+tok+'")'

def compilePattern(pattern, nr):
    ret = '// ' + pattern + '\n'
    ret = ret + 'static bool match' + str(nr) + '(const Token *tok) {\n'
    tokens = pattern.split(' ')
    gotoNextToken = ''
    for tok in tokens:
        if tok == '':
            continue
        ret = ret + gotoNextToken
        gotoNextToken = '    tok = tok->next();\n'

        # [abc]
        if (len(tok) > 2) and (tok[0] == '[') and (tok[-1] == ']'):
            ret = ret + '    if (!tok || tok->str().size()!=1U || !strchr("'+tok[1:-1]+'", tok->str()[0]))\n'
            ret = ret + '        return false;\n'

        # a|b|c
        elif tok.find('|') > 0:
            tokens2 = tok.split('|')
            logicalOp = None
            neg = None
            if "" in tokens2:
                ret = ret + '    if (tok && ('
                logicalOp = ' || '
                neg = ''
            else:
                ret = ret + '    if (!tok || !('
                logicalOp = ' || '
                neg = ''
            first = True
            for tok2 in tokens2:
                if tok2 == '':
                    continue
                if not first:
                    ret = ret + logicalOp
                first = False
                ret = ret + neg + compileCmd(tok2)

            if "" in tokens2:
                ret = ret + '))\n'
                ret = ret + '        tok = tok->next();\n'
                gotoNextToken = ''
            else:
                ret = ret + '))\n'
                ret = ret + '        return false;\n'

        # !!a
        elif tok[0:2]=="!!":
            ret = ret + '    if (tok && tok->str() == "' + tok[2:] + '")\n'
            ret = ret + '        return false;\n'
            gotoNextToken = '    tok = tok ? tok->next() : NULL;\n'

        else:
            ret = ret + '    if (!tok || !' + compileCmd(tok) + ')\n'
            ret = ret + '        return false;\n'
    ret = ret + '    return true;\n}\n'
    return ret

def findMatchPattern(line):
    
    pos1 = line.find('Token::Match(')
    if pos1 == -1:
        pos1 = line.find('Token::simpleMatch(')
    if pos1 == -1:
        return None

    parlevel = 0
    args = []
    argstart = 0
    pos = pos1
    inString = False
    while pos < len(line):
        if inString:
            if line[pos] == '\\':
                pos = pos + 1
            elif line[pos] == '"':
                inString = False
        elif line[pos] == '"':
            inString = True
        elif line[pos] == '(':
            parlevel = parlevel + 1
            if parlevel == 1:
                argstart = pos + 1
        elif line[pos] == ')':
            parlevel = parlevel - 1
            if parlevel == 0:
                ret = []
                ret.append(line[pos1:pos+1])
                for arg in args:
                    ret.append(arg)
                ret.append(line[argstart:pos])
                return ret
        elif line[pos] == ',' and parlevel == 1:
            args.append(line[argstart:pos])
            argstart = pos + 1
        pos = pos + 1

    return None

def convertFile(srcname, destname):
    fin = open(srcname, "rt")
    srclines = fin.readlines()
    fin.close()

    matchfunctions = ''
    matchfunctions = matchfunctions + '#include "token.h"\n'
    matchfunctions = matchfunctions + '#include <string>\n'
    matchfunctions = matchfunctions + '#include <cstring>\n'
    code = ''

    patternNumber = 1
    for line in srclines:
        res = findMatchPattern(line)
        if res == None:
            code = code + line
        elif len(res) != 3:
            code = code + line  # TODO: handle varid
        else:
            g0 = res[0]
            arg1 = res[1]
            arg2 = res[2]

            res = re.match(r'\s*"(.+)"\s*$', arg2)
            if res == None:
                code = code + line  # Non-const pattern - bailout
            else:
                arg2 = res.group(1)
                pos1 = line.find(g0)
                code = code + line[:pos1]+'match'+str(patternNumber)+'('+arg1+')'+line[pos1+len(g0):]
                matchfunctions = matchfunctions + compilePattern(arg2, patternNumber)
                patternNumber = patternNumber + 1

    fout = open(destname, 'wt')
    fout.write(matchfunctions+code)
    fout.close()

# selftests..
def testFindMatchPattern(arg1,pattern):
    res = findMatchPattern(' Token::Match(' + arg1 + ', "' + pattern + '") ')
    assert(res != None)
    assert(len(res) == 3)
    assert(res[0] == 'Token::Match(' + arg1 + ', "' + pattern + '")')
    assert(res[1] == arg1)
    assert(res[2] == ' "' + pattern + '"')
    res = findMatchPattern(' Token::simpleMatch(' + arg1 + ', "' + pattern + '") ')
    assert(res != None)
    assert(len(res) == 3)
    assert(res[0] == 'Token::simpleMatch(' + arg1 + ', "' + pattern + '")')
    assert(res[1] == arg1)
    assert(res[2] == ' "' + pattern + '"')
testFindMatchPattern('tok', ';')
testFindMatchPattern('tok->next()', ';')
testFindMatchPattern('Token::findsimplematch(tok,")")', ';')

# convert all lib/*.cpp files
for f in glob.glob('lib/*.cpp'):
    print f + ' => build/' + f[4:]
    convertFile(f, 'build/'+f[4:])

