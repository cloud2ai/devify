// Raw Email Saver Plugin for Haraka
// Captures and saves the complete raw email content

const fs = require('fs');
const path = require('path');

exports.register = function () {
    const plugin = this;
    const inbox_dir = process.env.EMAIL_INBOX_DIR || '/opt/haraka/emails/inbox';
    plugin.loginfo('Raw Email Saver plugin initialized');
    plugin.loginfo(`Emails will be saved to ${inbox_dir}/`);
    plugin.loginfo(`Using EMAIL_INBOX_DIR: ${process.env.EMAIL_INBOX_DIR || 'default (/opt/haraka/emails/inbox)'}`);
};

// Capture raw email data as it arrives
exports.hook_data = function (next, connection, data) {
    const transaction = connection.transaction;

    if (!transaction) {
        return next();
    }

    // Initialize email data collection
    if (!transaction._raw_email_data) {
        transaction._raw_email_data = [];
    }

    // Collect each data chunk
    if (data && data.length > 0) {
        transaction._raw_email_data.push(data);
        this.loginfo(
            `Collected data chunk: ${data.length} bytes`
        );
    }

    return next();
};

// Save the complete raw email using message_stream
exports.hook_queue = function (next, connection) {
    const plugin = this;
    const transaction = connection.transaction;

    if (!transaction) {
        plugin.logerror('No transaction found');
        return next(DENY, 'No transaction');
    }

    try {
        // Prepare directories - use environment variable with fallback
        // to container internal path
        // Get inbox directory from environment or use default path
        const inbox_dir = process.env.EMAIL_INBOX_DIR
            || '/opt/haraka/emails/inbox';
        if (!fs.existsSync(inbox_dir)) {
            fs.mkdirSync(inbox_dir, { recursive: true });
        }

        // File paths
        const eml_file = path.join(inbox_dir, `${transaction.uuid}.eml`);
        const meta_file = path.join(inbox_dir, `${transaction.uuid}.meta`);

        // Use message_stream to capture complete email
        if (transaction.message_stream) {
            plugin.loginfo(
                `Capturing complete email using message_stream`
            );

            // Create write stream to save the complete email
            const ws = fs.createWriteStream(eml_file);

            // Pipe the message stream to file
            transaction.message_stream.pipe(ws);

            ws.on('finish', () => {
                plugin.loginfo(
                    `Complete email stream saved to: ${eml_file}`
                );

                // Read the saved file to get its size and content info
                const stats = fs.statSync(eml_file);
                const saved_size = stats.size;

                // Create comprehensive metadata
                const metadata = {
                    uuid: transaction.uuid,
                    from: transaction.mail_from
                        ? transaction.mail_from.address()
                        : '',
                    to: transaction.rcpt_to
                        ? transaction.rcpt_to.map(r => r.address())
                        : [],
                    subject: transaction.header
                        ? (transaction.header.get('Subject') || '')
                        : '',
                    received_at: new Date().toISOString(),
                    saved_size: saved_size,
                    original_size: transaction.size || 0,
                    eml_file: eml_file,
                    status: 'inbox',
                    has_attachments: false,
                    is_multipart: false,
                    content_type: 'unknown'
                };

                // Read a portion of the file to analyze content
                try {
                    const file_content = fs.readFileSync(
                        eml_file,
                        'utf8'
                    );
                    metadata.has_attachments = file_content.includes(
                        'Content-Disposition: attachment'
                    );
                    metadata.is_multipart = file_content.includes(
                        'Content-Type: multipart'
                    );
                    metadata.content_type = file_content.includes(
                        'Content-Type: text/html'
                    ) ? 'html' : 'text';
                } catch (e) {
                    plugin.logwarn(
                        `Could not analyze saved email content: ${e.message}`
                    );
                }

                // Save metadata
                fs.writeFileSync(
                    meta_file,
                    JSON.stringify(metadata, null, 2),
                    'utf8'
                );

                plugin.loginfo(
                    `Complete email saved: ${transaction.uuid}`
                );
                plugin.loginfo(
                    `Saved: ${saved_size} bytes, ` +
                    `Original: ${transaction.size || 0} bytes`
                );
                plugin.loginfo(
                    `From: ${metadata.from} | To: ${metadata.to.join(', ')}`
                );

                const subject_preview = metadata.subject.substring(0, 50);
                const subject_suffix = metadata.subject.length > 50
                    ? '...'
                    : '';
                plugin.loginfo(
                    `Subject: ${subject_preview}${subject_suffix}`
                );

                if (metadata.has_attachments) {
                    plugin.loginfo('Email contains attachments');
                }
                if (metadata.is_multipart) {
                    plugin.loginfo('Email is multipart');
                }
            });

            ws.on('error', (err) => {
                plugin.logerror(
                    `Error writing email to file: ${err.message}`
                );
                next(DENY, 'Error saving email');
            });

            // Return OK immediately - the stream will handle the saving
            return next(OK, 'Complete email stream being saved');

        } else {
            plugin.logwarn(
                'No message_stream found, creating basic email'
            );

            // Fallback: create basic email structure
            const from_addr = transaction.mail_from
                ? transaction.mail_from.address()
                : '';
            const to_addrs = transaction.rcpt_to
                ? transaction.rcpt_to.map(r => r.address()).join(', ')
                : '';
            const subject = transaction.header
                ? (transaction.header.get('Subject') || 'No Subject')
                : 'No Subject';

            const raw_email = [
                `From: ${from_addr}\r\n`,
                `To: ${to_addrs}\r\n`,
                `Subject: ${subject}\r\n`,
                `Date: ${new Date().toISOString()}\r\n`,
                `Message-ID: <${transaction.uuid}@devify.local>\r\n`,
                `MIME-Version: 1.0\r\n`,
                `Content-Type: text/plain; charset=utf-8\r\n`,
                `\r\n`,
                `This email was received by Haraka.\r\n`,
                `UUID: ${transaction.uuid}\r\n`,
                `Original Size: ${transaction.size || 0} bytes\r\n`
            ].join('');

            // Save the basic email content
            fs.writeFileSync(eml_file, raw_email, 'utf8');

            // Create metadata
            const metadata = {
                uuid: transaction.uuid,
                from: transaction.mail_from
                    ? transaction.mail_from.address()
                    : '',
                to: transaction.rcpt_to
                    ? transaction.rcpt_to.map(r => r.address())
                    : [],
                subject: transaction.header
                    ? (transaction.header.get('Subject') || '')
                    : '',
                received_at: new Date().toISOString(),
                saved_size: raw_email.length,
                original_size: transaction.size || 0,
                eml_file: eml_file,
                status: 'inbox',
                has_attachments: false,
                is_multipart: false,
                content_type: 'text'
            };

            // Save metadata
            fs.writeFileSync(
                meta_file,
                JSON.stringify(metadata, null, 2),
                'utf8'
            );

            plugin.loginfo(
                `Basic email saved: ${transaction.uuid}`
            );
            plugin.loginfo(
                `Saved: ${raw_email.length} bytes, ` +
                `Original: ${transaction.size || 0} bytes`
            );

            return next(OK, 'Basic email saved successfully');
        }

    } catch (error) {
        plugin.logerror(
            `Error saving email: ${error.message}`
        );
        return next(DENY, 'Error saving email');
    }
};
