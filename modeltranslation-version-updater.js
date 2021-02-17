const VERSION_REGEX = /^VERSION = \((?<major>\d+), (?<minor>\d+), (?<patch>\d+), '(?<tag>\w+)', (?<tagVer>\d+)\)$/m;
const NEW_VERSION_REGEX = /(?<major>\d+).(?<minor>\d+).(?<patch>\d+)(-(?<tag>\w+).(?<tagVer>\d+))?/;

module.exports.readVersion = function (contents) {
  let v = contents.match(VERSION_REGEX).groups;
  let version = `${v.major}.${v.minor}.${v.patch}`;
  if (v.tag == "final")
    return version;
  return version + `-${v.tag}.${v.tagVer}`;
}

module.exports.writeVersion = function (contents, version) {
  let v = version.match(NEW_VERSION_REGEX).groups;
  return contents.replace(VERSION_REGEX, `VERSION = (${v.major}, ${v.minor}, ${v.patch}, '${v.tag || 'final'}', ${v.tagVer || 0})`);
}
