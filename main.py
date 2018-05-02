import chardet, datetime, email, imaplib, json, logging, os, pprint, sys
import email.utils

import pytz, requests

logging.basicConfig(
    # filename=os.environ['ANNX_PGSLP__LOG_PATH'],
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(module)s-%(funcName)s()::%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S',
    )
log = logging.getLogger(__name__)
log.debug( 'starting log' )


class Controller(object):
    """ Manages steps. """

    def __init__( self ):
        self.RECENTS_URL = os.environ['ANNX_PGSLP__RECENT_TRANSFERS_URL']
        self.RECENTS_PATH = os.environ['ANNX_PGSLP__RECENT_TRANSFERS_PATH']

    def transfer_requests( self ):
        """ Calls steps.
            Called by ```if __name__ == '__main__':``` """
        since_date = self.get_since_date()
        email_dct = self.check_email( since_date )  # dct contains date and body items.
        if email_dct['email_body']:
            pageslips = self.extract_pageslips( email_body )
            self.deposit_pageslips( pageslips )
            self.update_since_data( email_dct['email_date'] )
        log.debug( 'transfer-check complete' )
        return

    def get_since_date( self ):
        """ Grabs comparison date.
            Called by transfer_requests() """
        since_date = None
        r = requests.get( self.RECENTS_URL )
        log.debug( 'r.status_code, `%s`; type, `%s`' % (r.status_code, type(r.status_code))  )
        if r.status_code == 404:
            self.handle_date_json_not_found()
        else:
            recents = r.json()['recent_transfers']
            if recents:
                since_date = recents[-1].strptime( '%Y-%m-%dT%H:%M:%S.%f' )
        log.debug( 'since_date, `%s`' % since_date )
        return since_date

    def handle_date_json_not_found( self ):
        """ Creates recent_transfers.json.
            Called by get_since_date() """
        eastern = pytz.timezone( 'US/Eastern' )
        dt_obj = eastern.localize( datetime.datetime.now() )
        recents_dct = {
            'last_updated': dt_obj.strftime( '%Y-%m-%dT%H:%M:%S.%f%z' ),
            'recent_transfers': [] }
        with open( self.RECENTS_PATH, 'w+' ) as f:
            f.write( json.dumps(recents_dct, sort_keys=True, indent=2) )
        return

    def check_email( self, since_date ):
        """ Checks for recent annex-requests.
            Returns dct of email-date and email-body.
            Called by transfer_requests()"""
        checker = EmailChecker()
        email_dct = checker.check_email( since_date )
        return email_dct

    ## end class Controller()


class EmailChecker( object ):
    """ Manages email-check. """

    def __init__( self ):
        self.MAIL_DOMAIN = os.environ['ANNX_PGSLP__MAIL_DOMAIN']
        self.EMAIL = os.environ['ANNX_PGSLP__EMAIL']
        self.PASSWORD = os.environ['ANNX_PGSLP__PASSWORD']

    def check_email( self, since_date ):
        """ Manager for email check.
            Called by Controller.check_email() """
        mailer = self.setup_mailer()
        email_dct = self.search_email( mailer, since_date )
        self.close_mailer( mailer )
        log.debug( 'email_dct, ```%s```' % email_dct )
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

    def search_email( self, mailer, since_date ):
        """ Searches email account on proper subject.
            Called by check_email() """
        email_dct = { 'email_date': None, 'email_body': None }
        try:
            ( ok_response, id_list ) = mailer.search( 'utf-8', b'Subject', b'"Mail from the Library"' )  # response, eg, ```('OK', [b'2 3'])```
            log.debug( 'id_list, ```%s```' % id_list )
            email_dct = self.process_recent_email( mailer, since_date, id_list )
            return email_dct
        except Exception as e:
            log.error( 'exception, ```%s```' % e )
            if mailer:
                self.close_mailer( mailer )
            raise Exception( 'whoa: ```%s```' % e )




    def process_recent_email( self, mailer, since_date, id_list ):
        """ Checks last email date and if necessary, grabs body.
            Called by search_email() """
        email_dct = { 'email_date': None, 'email_body': None }
        email_obj = self.objectify_email_message( mailer, id_list )
        email_date = self.parse_email_date( email_obj )
        if since_date is not None and since_date > email_date:
            log.debug( 'no new email' )
            return email_dct
        body_message = self.parse_body_message( email_obj )

        email_dct['email_body'] = final
        log.debug( 'email_dct, ```%s```' % email_dct )
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
        log.debug( 'final, ```%s```' % final )
        return final

    # def process_recent_email( self, mailer, since_date, id_list ):
    #     """ Checks last email date and if necessary, grabs body.
    #         Called by search_email() """
    #     email_dct = { 'email_date': None, 'email_body': None }
    #     email_obj = self.objectify_email_message( mailer, id_list )
    #     email_date = self.parse_email_date( email_obj )
    #     if since_date is not None and since_date > email_date:
    #         log.debug( 'no new email' )
    #         return email_dct


    #     body_message = email_obj.get_payload( decode=True )  # body-content in bytes
    #     log.debug( 'type(body_message), `%s`' % type(body_message) )
    #     # log.debug( b'body_message, ```%s```' % body_message )
    #     try:
    #         final = body_message.decode( 'utf-8' )
    #     except UnicodeDecodeError:
    #         encoding_dct = chardet.detect( body_message )  # eg ```{'encoding': 'ISO-8859-1', 'confidence': 0.73, 'language': ''}```
    #         try:
    #             final = body_message.decode( encoding_dct['encoding'] )
    #         except Exception as e:
    #             log.error( 'exception, ```%s```' % e )
    #             final = body_message.decode('utf-8', errors='backslashreplace')
    #     log.debug( 'final, ```%s```' % final )
    #     email_dct['email_body'] = final
    #     log.debug( 'email_dct, ```%s```' % email_dct )
    #     return email_dct






    def close_mailer( self, mailer ):
        """ Closes mailer.
            Called by check_email() """
        mailer.close()
        mailer.logout()
        log.debug( 'mailer closed' )
        return


# ## connect
# try:
#     mailer = imaplib.IMAP4_SSL( MAIL_DOMAIN )
#     mailer.login( EMAIL, PASSWORD )
#     mailer.select( 'inbox' )   # connect's to inbox by default, but good to specify
#     log.debug( 'have mailer' )
# except Exception as e:
#     log.error( 'exception, ```%s```' % e )
#     if mailer:
#         log.debug( 'closing mailer and logging out' )
#         mailer.close()
#         mailer.logout()
#     raise Exception( 'whoa: ```%s```' % e )

# ## search
# try:
#     ( ok_response, id_list ) = mailer.search( 'utf-8', b'Subject', b'"test sierra_to_annex"' )  # response, eg, ```('OK', [b'2 3'])```
# except Exception as e:
#     log.error( 'exception, ```%s```' % e )
#     if mailer:
#         log.debug( 'closing mailer and logging out' )
#         mailer.close()
#         mailer.logout()

# ## process
# try:
#     recent_id = id_list[0].split()[-1]  # str; & id_list is really a list of a single space-delimited string
#     ( ok_response, rfc822_obj_list ) = mailer.fetch( recent_id, '(RFC822)' )
#     email_rfc822_tuple = rfc822_obj_list[0]
#     email_rfc822_bytestring = email_rfc822_tuple[1]  # tuple[0] example, ```b'3 (RFC822 {5049}'```
#     email_obj = email.message_from_string( email_rfc822_bytestring.decode('utf-8') )  # email is a standard python import
#     log.debug( 'is_multipart(), `%s`' % email_obj.is_multipart() )
#     items_list_of_tuples = email_obj.items()  # eg, [ ('Subject', 'the subject text'), () ] -- BUT does NOT provide body-content
#     log.debug( 'items_list_of_tuples, ```%s```' % pprint.pformat(items_list_of_tuples) )
#     body_message = email_obj.get_payload( decode=True )  # body-content in bytes
#     log.debug( 'type(body_message), `%s`' % type(body_message) )
#     log.debug( 'body_message, ```%s```' % body_message )
#     final = body_message.decode( 'utf-8' )
#     # final = urllib.parse.unquote( tmp )
#     log.debug( 'final, ```%s```' % final )
# except Exception as e:
#     log.error( 'exception, ```%s```' % e )
# finally:
#     if mailer:
#         log.debug( 'closing mailer and logging out' )
#         mailer.close()
#         mailer.logout()

# log.debug( 'EOF' )



if __name__ == '__main__':
    c = Controller()
    c.transfer_requests()
    log.debug( 'complete' )
