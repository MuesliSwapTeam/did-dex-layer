const express = require('express');
const jwt = require('express-jwt');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();

const app = express();
app.use(cors());
app.use(function (req, res, next) {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
});
const port = 6002;
const args = process.argv.slice(2);
const is_test_mode = args.length > 0 && args[0] === 'test';

const JWT_KEY = `
-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAM02J1ChYBxLhZD01iesq6eUnX7SeDRx
ffDg7fa/3aA/80HfHYjcAFkQriHdtIZQdn40IquxQnmUFfRgGx3yXIMCAwEAAQ==
-----END PUBLIC KEY-----`;

app.get('/status', jwt({ secret: JWT_KEY, algorithms: ['RS256'], ignoreExpiration: is_test_mode }), function (req, res) {
    if (!req.user && !is_test_mode) {
        return res.status(401).json({ message: 'Unauthorized' });
    }

    // Open the database
    let db = new sqlite3.Database('../users.db', sqlite3.OPEN_READONLY, (err) => {
        if (err) {
            console.error('Error opening database', err.message);
            return res.status(401).json({ message: err });
        }
        console.log('Connected to the users.db database.');
    });

    // SQL query to find the user
    const sql = `SELECT * FROM user WHERE connect_did = ?`;

    // Execute the query
    db.get(sql, [req.user.connectDid], (err, row) => {
        db.close();

        if (err) {
            console.error('Error executing SQL query', err.message);
            return res.status(401).json({ message: err });
        }

        // If a row is found, return it
        if (row) {
            console.log('User found:', row);
            res.json({ ...row, access_level: 1 });
        } else {
            console.log('User not found');
            res.json({ did: req.user.connectDid, access_level: 1 });
        }
    });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}/`);
});
