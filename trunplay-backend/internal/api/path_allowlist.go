package api

import (
	"path/filepath"
	"strings"
)

// resolvePathForAllowlist returns an absolute, cleaned path.
// If symlink resolution fails (e.g. path does not exist), it falls back to the
// absolute path instead of an empty value.
func resolvePathForAllowlist(path string) string {
	trimmed := strings.TrimSpace(path)
	if trimmed == "" {
		return ""
	}
	abs, err := filepath.Abs(trimmed)
	if err != nil {
		return filepath.Clean(trimmed)
	}
	resolved, err := filepath.EvalSymlinks(abs)
	if err == nil && resolved != "" {
		return filepath.Clean(resolved)
	}
	parentResolved, parentErr := filepath.EvalSymlinks(filepath.Dir(abs))
	if parentErr == nil && parentResolved != "" {
		return filepath.Clean(filepath.Join(parentResolved, filepath.Base(abs)))
	}
	return filepath.Clean(abs)
}

func absoluteCleanPath(path string) string {
	trimmed := strings.TrimSpace(path)
	if trimmed == "" {
		return ""
	}
	abs, err := filepath.Abs(trimmed)
	if err != nil {
		return filepath.Clean(trimmed)
	}
	return filepath.Clean(abs)
}

func appendCandidate(candidates []string, value string) []string {
	if value == "" {
		return candidates
	}
	for _, c := range candidates {
		if c == value {
			return candidates
		}
	}
	return append(candidates, value)
}

func isPathWithinRoot(path, root string) bool {
	if path == root {
		return true
	}
	if root == string(filepath.Separator) {
		return strings.HasPrefix(path, root)
	}
	return strings.HasPrefix(path, root+string(filepath.Separator))
}

func isPathWithinRoots(path string, roots []string) bool {
	pathCandidates := make([]string, 0, 2)
	pathCandidates = appendCandidate(pathCandidates, resolvePathForAllowlist(path))
	pathCandidates = appendCandidate(pathCandidates, absoluteCleanPath(path))
	if len(pathCandidates) == 0 {
		return false
	}

	for _, root := range roots {
		rootCandidates := make([]string, 0, 2)
		rootCandidates = appendCandidate(rootCandidates, resolvePathForAllowlist(root))
		rootCandidates = appendCandidate(rootCandidates, absoluteCleanPath(root))
		for _, pathCandidate := range pathCandidates {
			for _, rootCandidate := range rootCandidates {
				if isPathWithinRoot(pathCandidate, rootCandidate) {
					return true
				}
			}
		}
	}
	return false
}
