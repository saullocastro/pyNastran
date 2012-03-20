import sys
from datetime import date

import pyNastran
from pyNastran.op2.op2 import OP2


def makeStamp(Title):
    t = date.today()
    months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    today = '%s %s, %s' %(months[t.month],t.day,t.year)
    
    releaseDate = '02/08/12'#pyNastran.__releaseDate__
    releaseDate = ''
    build = 'pyNastran v%s %s' %(pyNastran.__version__,releaseDate)
    out = '1    %-52s   %20s %-22s PAGE ' %(Title,today,build)
    return out

def makePyNastranTitle():
    n = ''
    lines1 = [
    n+'/* -------------------------------------------------------------------  */\n',
    n+'/*                              PYNASTRAN                               */\n',
    n+'/*                      - NASTRAN FILE INTERFACE -                      */\n',
    n+'/*                                                                      */\n',
    n+'/*              A Python reader/editor/writer for the various           */\n',
    n+'/*                        NASTRAN file formats.                         */\n',
    n+'/*                  Copyright (C) 2011-2012 Steven Doyle                */\n',
    n+'/*                                                                      */\n',
    n+'/*    This program is free software; you can redistribute it and/or     */\n',
    n+'/*    modify it under the terms of the GNU Lesser General Public        */\n',
    n+'/*    License as published by the Free Software Foundation;             */\n',
    n+'/*    version 3 of the License.                                         */\n',
    n+'/*                                                                      */\n',
    n+'/*    This program is distributed in the hope that it will be useful,   */\n',
    n+'/*    but WITHOUT ANY WARRANTY; without even the implied warranty of    */\n',
    n+'/*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the      */\n',
    n+'/*    GNU Lesser General Public License for more details.               */\n',
    n+'/*                                                                      */\n',
    n+'/*    You should have received a copy of the GNU Lesser General Public  */\n',
    n+'/*    License along with this program; if not, write to the             */\n',
    n+'/*    Free Software Foundation, Inc.,                                   */\n',
    n+'/*    675 Mass Ave, Cambridge, MA 02139, USA.                           */\n',
    n+'/* -------------------------------------------------------------------  */\n',
    '\n']

    n = 46*' '
    lines2 = [
        n+'* * * * * * * * * * * * * * * * * * * *\n',
        n+'* * * * * * * * * * * * * * * * * * * *\n',
        n+'* *                                 * *\n',
        n+'* *            pyNastran            * *\n',
        n+'* *                                 * *\n',
        n+'* *                                 * *\n',
        n+'* *                                 * *\n',
        n+'* *        Version %8s       * *\n' %(pyNastran.__version__),
        n+'* *                                 * *\n',
        n+'* *                                 * *\n',
        n+'* *          %15s         * *\n' %(pyNastran.__releaseDate2__),
        n+'* *                                 * *\n',
        n+'* *            Questions            * *\n',
        n+'* *        mesheb82@gmail.com       * *\n',
        n+'* *                                 * *\n',
        n+'* *                                 * *\n',
        n+'* * * * * * * * * * * * * * * * * * * *\n',
        n+'* * * * * * * * * * * * * * * * * * * *\n']
    return ''.join(lines1+lines2)

def makeEnd():
    lines = [' \n'
             '1                                        * * * END OF JOB * * *\n'
             ' \n'
             ' \n']
    return ''.join(lines)


class F06Writer(object):
    def __init__(self,model='tria3'):
        self.model = model
        self.op2Name = model+'.op2'
        
    def run(self):
        op2 = OP2(self.op2Name)
        op2.readOP2()
        
        f06Name = '%s.f06.out' %(self.model)
        f = open(f06Name,'wb')
        f.write(makePyNastranTitle())
        
        pageStamp = '1    MSC.NASTRAN JOB CREATED ON 10-DEC-07 AT 09:21:23                      NOVEMBER  14, 2011  MSC.NASTRAN  6/17/05   PAGE '
        
        pageNum = 1
        header = ['','','']  # subcase name, subcase ID, transient word & value
        for case,result in sorted(op2.displacements.items()):
            msg = result.writeF06(header,pageStamp,pageNum=pageNum)
            f.write(msg)
            pageNum +=1

        for case,result in sorted(op2.plateStrain.items()):
            (msg,pageNum) = result.writeF06(header,pageStamp,pageNum=pageNum)
            f.write(msg)

        for case,result in sorted(op2.plateStress.items()):
            (msg,pageNum) = result.writeF06(header,pageStamp,pageNum=pageNum)
            f.write(msg)

        f.write(makeEnd())
        f.close()
        

if __name__=='__main__':
    #Title = 'MSC.NASTRAN JOB CREATED ON 10-DEC-07 AT 09:21:23'
    #stamp = makeStamp(Title) # doesnt have pageNum
    #print "|%s|" %(stamp+'22')
    
    model = sys.argv[1]
    f06 = F06Writer(model)
    f06.run()


