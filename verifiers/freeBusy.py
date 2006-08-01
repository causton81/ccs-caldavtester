##
# Copyright (c) 2006 Apple Computer, Inc. All rights reserved.
#
# This file contains Original Code and/or Modifications of Original Code
# as defined in and that are subject to the Apple Public Source License
# Version 2.0 (the 'License'). You may not use this file except in
# compliance with the License. Please obtain a copy of the License at
# http://www.opensource.apple.com/apsl/ and read it before using this
# file.
#
# The Original Code and all software distributed under the License are
# distributed on an 'AS IS' basis, WITHOUT WARRANTY OF ANY KIND, EITHER
# EXPRESS OR IMPLIED, AND APPLE HEREBY DISCLAIMS ALL SUCH WARRANTIES,
# INCLUDING WITHOUT LIMITATION, ANY WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE, QUIET ENJOYMENT OR NON-INFRINGEMENT.
# Please see the License for the specific language governing rights and
# limitations under the License.
#
# DRI: Cyrus Daboo, cdaboo@apple.com
##

"""
Verifier that checks the response of a free-busy-query.
"""
import StringIO
from vobject.icalendar import periodToString
import datetime
from vobject.base import VObjectError
from vobject.base import readOne

class Verifier(object):
    
    def verify(self, uri, response, respdata, args): #@UnusedVariable
        
        # Must have status 200
        if response.status != 200:
            return False, "        HTTP Status Code Wrong: %d" % (response.status,)

        # Get expected FREEBUSY info
        busy = args.get("busy", [])
        tentative = args.get("tentative", [])
        unavailable = args.get("unavailable", [])
        
        # Parse data as calendar object
        try:
            s = StringIO.StringIO(respdata)
            calendar = readOne(s)
            
            # Check for calendar
            if calendar.name != "VCALENDAR":
                raise ValueError("Top-level component is not a calendar: %s" % (calendar.name, ))
            
            # Only one component
            comps = list(calendar.components())
            if len(comps) != 1:
                raise ValueError("Wrong number of components in calendar")
            
            # Must be VFREEBUSY
            fb = comps[0]
            if fb.name != "VFREEBUSY":
                raise ValueError("Calendar contains unexpected component: %s" % (fb.name, ))
            
            # Extract periods
            busyp = []
            tentativep = []
            unavailablep = []
            for fp in [x for x in fb.lines() if x.name == "FREEBUSY"]:
                periods = fp.value
                # Convert start/duration to start/end
                for i in range(len(periods)):
                    if isinstance(periods[i][1], datetime.timedelta):
                        periods[i] = (periods[i][0], periods[i][0] + periods[i][1])
                # Check param
                fbtype = "BUSY"
                if "FBTYPE" in fp.params:
                    fbtype = fp.params["FBTYPE"][0]
                if fbtype == "BUSY":
                    busyp.extend(periods)
                elif fbtype == "BUSY-TENTATIVE":
                    tentativep.extend(periods)
                elif fbtype == "BUSY-UNAVAILABLE":
                    unavailablep.extend(periods)
                else:
                    raise ValueError("Unknown FBTYPE: %s" % (fbtype,))
            
            # Set sizes must match
            if (len(busy) != len(busyp) or
                 len(unavailable) != len(unavailablep) or
                 len(tentative) != len(tentativep)):
                raise ValueError("Period list sizes do not match.")
            
            # Convert to string sets
            busy = set(busy)
            busyp[:] = [periodToString(x) for x in busyp]
            busyp = set(busyp)
            tentative = set(tentative)
            tentativep[:] = [periodToString(x) for x in tentativep]
            tentativep = set(tentativep)
            unavailable = set(unavailable)
            unavailablep[:] = [periodToString(x) for x in unavailablep]
            unavailablep = set(unavailablep)

            # Compare all periods
            if len(busyp.symmetric_difference(busy)):
                raise ValueError("Busy periods do not match")
            elif len(tentativep.symmetric_difference(tentative)):
                raise ValueError("Busy-tentative periods do not match")
            elif len(unavailablep.symmetric_difference(unavailable)):
                raise ValueError("Busy-unavailable periods do not match")
                
        except VObjectError:
            return False, "        HTTP response data is not a calendar"
        except ValueError, txt:
            return False, "        HTTP response data is invalid: %s" % (txt,)
            
        return True, ""
