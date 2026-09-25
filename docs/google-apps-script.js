/**
 * App Fee Waiver – Funding Testimonies feed (Google Apps Script, free)
 *
 * Paste this into the Google Sheet that collects your testimony form responses:
 *   Extensions → Apps Script → replace everything with this file → Save.
 * Then follow docs/GOOGLE_SHEET_SETUP.md (set the token, deploy as a web app).
 *
 * What it does: when the website asks (with the secret token), it returns ONLY the
 * rows where the "Approved" column is YES. Nothing else in your sheet is shared.
 */

// Name of the tab that holds the form responses (Google's default is "Form Responses 1").
var SHEET_NAME = "Form Responses 1";

function doGet(e) {
  var expected = PropertiesService.getScriptProperties().getProperty("SYNC_TOKEN");
  var token = (e && e.parameter && e.parameter.token) || "";
  if (!expected) return json_({ error: "SYNC_TOKEN script property is not set." });
  if (token !== expected) return json_({ error: "Invalid token." });

  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  if (!sheet) return json_({ error: "Sheet tab '" + SHEET_NAME + "' not found." });

  var values = sheet.getDataRange().getValues();
  if (values.length < 2) return json_({ rows: [] });

  var headers = values[0].map(function (h) { return String(h).trim(); });
  var approvedCol = -1, timestampCol = -1, emailCol = -1;
  headers.forEach(function (h, i) {
    var k = h.toLowerCase();
    if (approvedCol < 0 && k.indexOf("approved") === 0) approvedCol = i;
    if (timestampCol < 0 && k.indexOf("timestamp") === 0) timestampCol = i;
    if (emailCol < 0 && k.indexOf("email") >= 0) emailCol = i;
  });
  if (approvedCol < 0) return json_({ error: "Add a column named 'Approved' to the sheet." });

  var tz = Session.getScriptTimeZone();
  var rows = [];
  for (var r = 1; r < values.length; r++) {
    var row = values[r];
    if (String(row[approvedCol]).trim().toUpperCase() !== "YES") continue;

    var item = {};
    headers.forEach(function (h, i) {
      if (!h) return;
      var v = row[i];
      item[h] = v instanceof Date ? Utilities.formatDate(v, tz, "yyyy-MM-dd'T'HH:mm:ssXXX") : String(v);
    });
    // Stable ID so the website never creates duplicates, even if rows are re-sorted.
    var email = emailCol >= 0 ? item[headers[emailCol]] : "";
    var idSource = timestampCol >= 0 ? item[headers[timestampCol]] + "|" + email : "row-" + r;
    item._id = md5_(idSource);
    rows.push(item);
  }
  return json_({ rows: rows });
}

function md5_(text) {
  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, text, Utilities.Charset.UTF_8);
  return bytes.map(function (b) { return ("0" + (b & 0xff).toString(16)).slice(-2); }).join("");
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
