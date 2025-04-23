def get_html_content(link):
    return f'''
    <table border="0" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse">
        <tbody>
            <tr>
                <td width="100%" align="center">
                    <table border="0" cellspacing="0" cellpadding="0" align="center" style="border-collapse:collapse">
                        <tbody>
                            <tr>
                                <td width="1160" align="center">
                                    <div style="max-width:580px;margin:0 auto" dir="ltr" bgcolor="#ffffff">
                                        <table border="0" cellspacing="0" cellpadding="0" align="center" id="email_table" style="border-collapse:collapse;max-width:580px;margin:0 auto">
                                            <tbody>
                                                <tr>
                                                    <td id="email_content" style="font-family:Helvetica Neue,Helvetica,Lucida Grande,tahoma,verdana,arial,sans-serif;background:#ffffff">
                                                        <table border="0" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse">
                                                            <tbody>
                                                                <tr>
                                                                    <td height="20" style="line-height:20px" colspan="3">&nbsp;</td>
                                                                </tr>
                                                                <tr>
                                                                    <td height="1" colspan="3" style="line-height:1px">
                                                                        <span style="color:#ffffff;font-size:1px;opacity:0">Facebook şifrenizi yenilemek için bir talep aldık.</span>
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td width="15" style="display:block;width:15px">&nbsp;&nbsp;&nbsp;</td>
                                                                    <td>
                                                                        <table border="0" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse">
                                                                            <tbody>
                                                                                <tr>
                                                                                    <td height="15" style="line-height:15px" colspan="3">&nbsp;</td>
                                                                                </tr>
                                                                                <tr>
                                                                                    <td width="32" align="left" valign="middle" style="height:32;line-height:0px">
                                                                                        <img width="32" src="https://static.xx.fbcdn.net/rsrc.php/v4/yS/r/ZirYDPWh0YD.png" height="32" style="border:0">
                                                                                    </td>
                                                                                    <td width="15" style="display:block;width:15px">&nbsp;&nbsp;&nbsp;</td>
                                                                                    <td width="100%">
                                                                                        <span style="font-family:Helvetica Neue,Helvetica,Lucida Grande,tahoma,verdana,arial,sans-serif;font-size:19px;line-height:32px;color:#1877f2"></span>
                                                                                    </td>
                                                                                </tr>
                                                                            </tbody>
                                                                        </table>
                                                                        <div style="margin-top:16px;margin-bottom:20px;font-size:18px">Merhaba,</div>
                                                                        <div style="border-bottom:solid 1px #e5e5e5;margin-bottom:20px"></div>
                                                                        <p style="font-size:16px">Şifrenizi doğrudan değiştirebilirsiniz.</p>
                                                                        <table border="0" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse">
                                                                            <tbody>
                                                                                <tr>
                                                                                    <td style="background:#1877f2;border-radius:6px;text-align:center;padding:12px 20px">
                                                                                        <a href="{link}" style="color:#fff;text-decoration:none;font-family:Roboto,sans-serif;font-size:17px;font-weight:500;display:block;width:100%">Şifreyi Değiştir</a>
                                                                                    </td>
                                                                                </tr>
                                                                            </tbody>
                                                                        </table>
                                                                        <div style="margin-top:20px">
                                                                            <span style="color:#333333;font-weight:bold">Böyle bir istekte bulunmadınız mı?</span>
                                                                        </div>
                                                                        <p>Yeni bir şifre isteğinde bulunmadıysanız, <a href="#" style="color:#0a7cff;text-decoration:none">bize bildirin</a>.</p>
                                                                    </td>
                                                                    <td width="15" style="display:block;width:15px">&nbsp;&nbsp;&nbsp;</td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                        <table border="0" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;margin-top:20px;border-top:1px solid #e5e5e5">
                                                            <tbody>
                                                                <tr>
                                                                    <td align="center" style="padding:20px;color:#84878b;font-size:11px;font-family:Roboto,sans-serif">
                                                                        <div style="margin-bottom:10px;color:#84878b">from</div>
                                                                        <img width="74" alt="Meta" height="22" src="https://facebook.com/images/email/meta_logo.png" style="border:0;margin-bottom:10px">
                                                                        <br>© Facebook. Meta Platforms, Inc., Attention: Community Support, 1 Meta Way, Menlo Park, CA 94025
                                                                        <br><br>Bu mesaj <a style="color:#1b74e4;text-decoration:none" href="mailto:burakpekisik@gmail.com">burakpekisik@gmail.com</a> adresine gönderilmiştir.
                                                                        <br>Hesabınızı güvende tutabilmek için lütfen bu e-postayı iletmeyin.
                                                                    </td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </td>
            </tr>
        </tbody>
    </table>
    '''
