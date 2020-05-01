const VERSION_REGEX = /^Version: (.*)$/m;

module.exports.readVersion = function (contents) {
  return contents.match(VERSION_REGEX)[1];
}

module.exports.writeVersion = function (contents, version) {
  return contents.replace(VERSION_REGEX, `Version: ${version}`);
}
