transfer annex page-slips
=========================

Code to get page-slip data from our ILS, Sierra, to our offsite-storage-facility.

---


#### background...

Patrons sometimes request items which are stored at the "Annex", the [Brown Library's](https://library.brown.edu) offsite storage facility. The result, we need to get this request data out of the [ILS](https://en.wikipedia.org/wiki/Integrated_library_system) so the data can be massaged and fed into the Annex's [inventory-control software](https://www.gfatech.com).

We _used_ to do this via [code](https://github.com/Brown-University-Library/josiah_print_pageslips) which mimicked human key-presses to the [Millennium](https://www.iii.com/products/millennium-ils/) character-based interface. The upgrade to [Sierra](https://www.iii.com/products/sierra-ils/) removed that functionality.

The folk that are most experienced with Sierra determined our best approach would be to use the 'auto-notices' feature, which allows for data to be prepared and then emailed or exported. Unfortunately, the Sierra vendor, [III](https://en.wikipedia.org/wiki/Innovative_Interfaces), does not offer [secure FTP](https://en.wikipedia.org/wiki/Secure_file_transfer_program) export for auto-notices data, so the pageslip data is auto-emailed to a developer-accessible email address.

This code, triggered by [cron](https://en.wikipedia.org/wiki/Cron), checks for new pageslip emails, parses out the pageslip data, and deposits it in a location where [other code](https://github.com/birkin/annex_process_pageslips) then massages that pageslip data and feeds it to the Annex's inventory-control software.


#### more info...

- Sierra ILS info, <bonnie_buzzell@brown.edu>

- code info, <birkin_diana@brown.edu>


#### license...

The [MIT License](https://en.wikipedia.org/wiki/MIT_License) (MIT)

Copyright (c) 2018 Brown University Library

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---
