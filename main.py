import email, imaplib, logging, os, pprint, re, subprocess, sys, urllib


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
        self.MAIL_DOMAIN = os.environ['ANNX_PGSLP__MAIL_DOMAIN']
        self.EMAIL = os.environ['ANNX_PGSLP__EMAIL']
        self.PASSWORD = os.environ['ANNX_PGSLP__PASSWORD']

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
        pass

    ## end class Controller()



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
