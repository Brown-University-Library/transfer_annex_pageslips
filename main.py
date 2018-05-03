import chardet, datetime, email, imaplib, json, logging, os, pprint, sys
import email.utils

import pytz, requests

logging.basicConfig(
    filename=os.environ['ANNX_PGSLP__LOG_PATH'],
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S',
    )
log = logging.getLogger(__name__)
log.debug( '\n\nstarting log\n============' )


class Controller(object):
    """ Manages steps. """

    def __init__( self ):
        self.RECENTS_URL = os.environ['ANNX_PGSLP__RECENT_TRANSFERS_URL']
        self.RECENTS_PATH = os.environ['ANNX_PGSLP__RECENT_TRANSFERS_PATH']
        self.DESTINATION_FILEPATH = os.environ['ANNX_PGSLP__DESTINATION_FILEPATH']
        self.recents_dct = None  # populated by get_last_transfer_date()

    def transfer_requests( self ):
        """ Calls steps.
            Called by ```if __name__ == '__main__':``` """
        last_transfer_date = self.get_last_transfer_date()
        email_dct = self.initiate_check_email( last_transfer_date )  # dct contains date and body items.
        if email_dct['email_body']:
            self.transfer_pageslips( email_dct['email_body'] )
            self.update_since_data( email_dct['email_date'] )
        log.debug( 'transfer-check complete' )
        return

    def get_last_transfer_date( self ):
        """ Grabs comparison date.
            Called by transfer_requests() """
        last_transfer_date = None
        r = requests.get( self.RECENTS_URL )
        self.recents_dct = self.get_recents( r )
        if self.recents_dct['recent_transfers']:
            last_transfer_date_str = self.recents_dct['recent_transfers'][-1]
            last_transfer_date = datetime.datetime.strptime( last_transfer_date_str, '%Y-%m-%dT%H:%M:%S.%f%z' )
        else:
            last_transfer_date = None
        log.debug( 'last_transfer_date, `%s`' % last_transfer_date )
        return last_transfer_date

    def get_recents( self, resp ):
        if resp.status_code == 404:
            recents_dct = self.create_recents_json()
        else:
            recents_dct = resp.json()
        log.debug( 'recents_dct, ```%s```' % pprint.pformat(recents_dct) )
        return recents_dct

    def create_recents_json( self ):
        """ Creates recent_transfers.json.
            Called by get_last_transfer_date() """
        eastern = pytz.timezone( 'US/Eastern' )
        dt_obj = eastern.localize( datetime.datetime.now() )
        recents_dct = {
            'last_updated': dt_obj.strftime( '%Y-%m-%dT%H:%M:%S.%f%z' ),
            'recent_transfers': [] }
        log.debug( 'recents_dct, ```%s```' % pprint.pformat(recents_dct) )
        with open( self.RECENTS_PATH, 'w+' ) as f:
            f.write( json.dumps(recents_dct, sort_keys=True, indent=2) )
        return recents_dct

    def initiate_check_email( self, last_transfer_date ):
        """ Checks for recent annex-requests.
            Returns dct of email-date and email-body.
            Called by transfer_requests()"""
        checker = EmailChecker()
        email_dct = checker.check_email( last_transfer_date )
        log.debug( 'returning email_dct' )
        return email_dct

    def transfer_pageslips( self, pageslips_data ):
        """ Transfers pageslips to destination.
            Called by transfer_requests() """
        try:
            with open( self.DESTINATION_FILEPATH, 'w+' ) as f:
                f.write( pageslips_data )
            log.debug( 'transfer successful' )
        except Exception as e:
            log.error( 'exception, ```%s```' % e )
            raise Exception( e )
        return

    def update_since_data( self, email_dt_obj ):
        """ Adds last-checked date to recents-tracker.
            Called by transfer_requests() """
        email_dt_str = email_dt_obj.strftime( '%Y-%m-%dT%H:%M:%S.%f%z' )
        self.recents_dct['recent_transfers'].append( email_dt_str )
        self.recents_dct['recent_transfers'] = self.recents_dct['recent_transfers'][-60:]  # storing a month's worth (assuming two-transfers a day)
        eastern = pytz.timezone( 'US/Eastern' )
        now_dt_obj = eastern.localize( datetime.datetime.now() )
        now_dt_str = now_dt_obj.strftime( '%Y-%m-%dT%H:%M:%S.%f%z' )
        self.recents_dct['last_updated'] = now_dt_str
        log.debug( 'self.recents_dct, ```%s```' % pprint.pformat(self.recents_dct) )
        with open( self.RECENTS_PATH, 'w+' ) as f:
            f.write( json.dumps(self.recents_dct, sort_keys=True, indent=2) )
        return

    ## end class Controller()


class EmailChecker( object ):
    """ Manages email-check. """

    def __init__( self ):
        self.MAIL_DOMAIN = os.environ['ANNX_PGSLP__MAIL_DOMAIN']
        self.EMAIL = os.environ['ANNX_PGSLP__EMAIL']
        self.PASSWORD = os.environ['ANNX_PGSLP__PASSWORD']
        self.SUBJECT = os.environ['ANNX_PGSLP__SUBJECT'].encode( 'utf-8' )
        self.FROM_SEGMENT = os.environ['ANNX_PGSLP__FROM_SEGMENT'].encode( 'utf-8' )

    def check_email( self, last_transfer_date ):
        """ Manager for email check.
            Called by Controller.initiate_check_email() """
        mailer = self.setup_mailer()
        email_dct = self.search_email( mailer, last_transfer_date )
        self.close_mailer( mailer )
        log.debug( 'email_dct, ```%s```' % pprint.pformat(email_dct)[0:100] )
        return email_dct

    def setup_mailer( self ):
        """ Sets up mailer & connects to inbox.
            Called by check_email() """
        try:
            mailer = imaplib.IMAP4_SSL( self.MAIL_DOMAIN )
            mailer.login( self.EMAIL, self.PASSWORD )
            mailer.select( 'inbox' )   # connect's to inbox by default, but good to specify
            log.debug( 'have mailer' )
            return mailer
        except Exception as e:
            log.error( 'exception, ```%s```' % e )
            raise Exception( 'whoa: ```%s```' % e )

    def search_email( self, mailer, last_transfer_date ):
        """ Searches email account on proper subject.
            Called by check_email()
            Note: B.B. says the `Subject` cannot be customized, but has added identifying text to the beginning of the body_message.
                  Perhaps in the future the email should be checked for this identifying text. """
        email_dct = { 'email_date': None, 'email_body': None }
        try:
            ( ok_response, id_list ) = mailer.search( 'utf-8', b'Subject', b'"%s"' % self.SUBJECT )  # response, eg, ```('OK', [b'2 3'])```
            log.debug( 'id_list, ```%s```' % id_list )
            email_dct = self.process_recent_email( mailer, last_transfer_date, id_list )
            return email_dct
        except Exception as e:
            log.error( 'exception, ```%s```' % e )
            if mailer:
                self.close_mailer( mailer )
            raise Exception( 'whoa: ```%s```' % e )

    def process_recent_email( self, mailer, last_transfer_date, id_list ):
        """ Checks last email date and if necessary, grabs body.
            Called by search_email() """
        email_dct = { 'email_date': None, 'email_body': None }
        email_obj = self.objectify_email_message( mailer, id_list )
        email_dct['email_date'] = self.parse_email_date( email_obj )  # datetime-obj
        if last_transfer_date is not None and last_transfer_date >= email_dct['email_date']:
            log.debug( 'no new email' )
            return email_dct
        body_message = self.parse_body_message( email_obj )
        email_dct['email_body'] = body_message
        log.debug( 'email_dct, ```%s```' % pprint.pformat(email_dct)[0:100] )
        return email_dct

    def objectify_email_message( self, mailer, id_list ):
        """ Returns recent email from id_list.
            Called by: process_recent_email() """
        recent_id = id_list[0].split()[-1]  # str; & id_list is really a list of a single space-delimited string
        ( ok_response, rfc822_obj_list ) = mailer.fetch( recent_id, '(RFC822)' )
        email_rfc822_tuple = rfc822_obj_list[0]  # tuple[0] example, ```b'3 (RFC822 {5049}'```
        email_rfc822_bytestring = email_rfc822_tuple[1]  # tuple[1] contains all the email data
        email_obj = email.message_from_string( email_rfc822_bytestring.decode('utf-8') )  # email is a standard python import
        return email_obj

    def parse_email_date( self, email_obj ):
        """ Returns date object.
            Called by process_recent_email() """
        dt_str = 'init'
        items_list_of_tuples = email_obj.items()  # eg, [ ('Subject', 'the subject text'), () ] -- BUT does NOT provide body-content
        log.debug( 'items_list_of_tuples, ```%s```' % pprint.pformat(items_list_of_tuples) )
        for tpl in items_list_of_tuples:
            if tpl[0] == 'Date':
                dt_str = tpl[1]
                break
        log.debug( 'dt_str, `%s`; type(), `%s`' % (dt_str, type(dt_str)) )
        dt_obj = email.utils.parsedate_to_datetime( dt_str )
        log.debug( 'dt_obj, `%s`' % str(dt_obj) )
        return dt_obj

    def parse_body_message( self, email_obj ):
        """ Returns body message.
            Called by process_recent_email() """
        body_message = email_obj.get_payload( decode=True )  # body-content in bytes
        try:
            final = body_message.decode( 'utf-8' )
        except UnicodeDecodeError:
            try:
                final = body_message.decode( chardet.detect( body_message )['encoding'] )  # chardet result, eg ```{'encoding': 'ISO-8859-1', 'confidence': 0.73, 'language': ''}```
            except Exception as e:
                log.error( 'exception, ```%s```' % e )
                final = body_message.decode('utf-8', errors='backslashreplace')
        log.debug( 'final, ```%s```' % final[0:100] )
        return final

    def close_mailer( self, mailer ):
        """ Closes mailer.
            Called by check_email() """
        log.debug( 'starting close_mailer()' )
        mailer.close()
        mailer.logout()
        log.debug( 'mailer closed' )
        return

    ## end class EmailChecker()


if __name__ == '__main__':
    c = Controller()
    c.transfer_requests()
    log.debug( 'complete' )
