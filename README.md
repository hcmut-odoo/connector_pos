[![License: AGPL-3](https://img.shields.io/badge/licence-AGPL--3-blue.svg)](http://www.gnu.org/licenses/agpl-3.0-standalone.html)


# Odoo Pos Connector


This module connects Odoo and [Pos](https://github.com/hcmut-odoo/pos).

Pos (https://github.com/hcmut-odoo/pos) is a simple e-commerce platform
written in Laravel/MySQL and published under the Open Software licence MIT.

This module allows the synchronization of the following objects from Pos
to Odoo:

* Websites
* Stores
* Carriers
* Invoices
* Orders
* Product categories
* Products
* Customers

Once these objects are synchronised, it will allow the import of sales orders,
together with the related customers.

As an extra feature, you can also export the stock quantities back to
Pos.

Installation
============

It doesn't require any plug-in in Pos, but requires an extra Python
library in Odoo server side, called pospyt:

https://github.com/hcmut-odoo/pospyt/

You can use pip install system to install it

```bash
git clone https://github.com/hcmut-odoo/pospyt/
```

Configuration
=============

To configure this module, you need to set several things in both Pos
and Odoo:

Steps in Pos
-------------------

- Go to the control panel (usually at <url>/admin).
- Login into the system.
- Go to *Advanced Parameters > Web service*
- Add a new entry.
- Generate a new API key that will be needed later.
- Grant all the needed access according your security policy.

Steps in Odoo
-------------

- Go to *Connectors > Pos > Backends*.
- Create a new record for registering a Pos backend. You will bind
   this backend to an specific company and warehouse.
- Define the main URL of the Pos web, and the webservice key you
   got in Pos.
- Define other parameters like the discount and shipping products, or if the
   taxes are included in the price.
- Click on "Synchronize Metadata" button. This will bring the basic shop
   information.
- Click on "Synchronize Base Data" button. This will import carriers,
   languages, tax groups and the rest of base data that are needed for the
   proper work.
- Go to *Accounting > Configuration > Taxes > Tax Groups*, and include
   for each of the tax definition imported from Pos, the corresponding
   taxes in Odoo.
- Activate the job runner, checking the connector documentation for setting
   the server correctly for using it in
   http://odoo-connector.com/guides/jobrunner.html
- Alternatively, if you are not able to activate it, you can enable the
   scheduled job called "Enqueue Jobs".
- Activate the scheduled jobs for importing the records you want:

  * Pos - Export Stock Quantities
  * Pos - Import Carriers
  * Pos - Import Customers
  * Pos - Import Products and Categories
  * Pos - Import Sales Orders
  * Pos - Payment methods

Usage
=====

To use this module, you need to:

- Go to *Connectors > Queue > Jobs*, and check the correct enqueuing of
   the tasks.
- Check on each menu the resulting imported records (Customers, Sales
   Orders...)


Test dependencies
=================

Extra libs are required to run the tests:
* ``vcrpy``
* ``freezegun``

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/hcmut-odoo/connector-pos/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Võ Qúy Long <long.vo2k1@hcmut.edu.vn>
* Nguyễn Xuân Vũ <vu.nguyen.ys.20gg@hcmut.edu.vn>
* Hà Phương Điền <dien.haphuong0526@hcmut.edu.vn>

This module is maintained by the HCMUT Odoo.

HCMUT Odoo, or the Ho Chi Minh University of Technology Odoo, is a nonprofit organization whose thesis topic is related to application development odoo erp.

To contribute to this module, please visit https://github.com/hcmut-odoo