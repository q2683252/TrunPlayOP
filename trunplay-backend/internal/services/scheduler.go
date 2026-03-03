package services

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
)

const crontabCommentPrefix = "# trunplay "

type Scheduler struct {
	mu            sync.Mutex
	crontabFile   string
	triggerScript string
}

func NewScheduler(crontabFile, triggerScript string) *Scheduler {
	return &Scheduler{crontabFile: crontabFile, triggerScript: triggerScript}
}

// parseStartTime parses "HH:MM" or "H:MM" into minute and hour. Returns 0, 0 if invalid.
func parseStartTime(startTime string) (minute, hour int) {
	parts := strings.SplitN(strings.TrimSpace(startTime), ":", 2)
	if len(parts) != 2 {
		return 0, 0
	}
	h, err1 := strconv.Atoi(strings.TrimSpace(parts[0]))
	m, err2 := strconv.Atoi(strings.TrimSpace(parts[1]))
	if err1 != nil || err2 != nil {
		return 0, 0
	}
	if h < 0 || h > 23 || m < 0 || m > 59 {
		return 0, 0
	}
	return m, h
}

// repeatDaysToCron converts repeat_days "0,1,2,3,4,5,6" (Sun-Sat) to cron day-of-week field.
// If empty or invalid, returns "*" (every day).
func repeatDaysToCron(repeatDays string) string {
	s := strings.TrimSpace(repeatDays)
	if s == "" {
		return "*"
	}
	parts := strings.Split(s, ",")
	var days []int
	for _, p := range parts {
		d, err := strconv.Atoi(strings.TrimSpace(p))
		if err != nil || d < 0 || d > 6 {
			continue
		}
		days = append(days, d)
	}
	if len(days) == 0 {
		return "*"
	}
	if len(days) == 7 {
		return "*"
	}
	// 0=Sun, 1=Mon, ..., 6=Sat (standard cron)
	out := make([]string, len(days))
	for i, d := range days {
		out[i] = strconv.Itoa(d)
	}
	return strings.Join(out, ",")
}

func (s *Scheduler) readCrontab() ([]string, error) {
	data, err := os.ReadFile(s.crontabFile)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	var lines []string
	sc := bufio.NewScanner(strings.NewReader(string(data)))
	for sc.Scan() {
		lines = append(lines, sc.Text())
	}
	return lines, sc.Err()
}

func (s *Scheduler) writeCrontab(lines []string) error {
	dir := filepath.Dir(s.crontabFile)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	data := strings.Join(lines, "\n")
	if len(lines) > 0 && !strings.HasSuffix(data, "\n") {
		data += "\n"
	}
	return os.WriteFile(s.crontabFile, []byte(data), 0644)
}

// removePlanEntries removes lines that belong to planID (comment + cron line).
func (s *Scheduler) removePlanEntries(lines []string, planID string) []string {
	triggerMarker := s.triggerScript + " " + planID
	commentMarker := crontabCommentPrefix + planID
	var out []string
	skipNext := false
	for _, line := range lines {
		if skipNext {
			skipNext = false
			continue
		}
		trimmed := strings.TrimSpace(line)
		if trimmed == commentMarker {
			skipNext = true
			continue
		}
		if strings.Contains(line, triggerMarker) {
			continue
		}
		out = append(out, line)
	}
	return out
}

func (s *Scheduler) SchedulePlan(planID, planTitle, startTime, repeatDays string, skipHolidays bool) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	minute, hour := parseStartTime(startTime)
	dow := repeatDaysToCron(repeatDays)
	cronLine := fmt.Sprintf("%d %d * * %s %s %s", minute, hour, dow, s.triggerScript, planID)
	lines, err := s.readCrontab()
	if err != nil {
		return false
	}
	if lines == nil {
		lines = []string{}
	}
	lines = s.removePlanEntries(lines, planID)
	lines = append(lines, crontabCommentPrefix+planID)
	lines = append(lines, cronLine)
	if err := s.writeCrontab(lines); err != nil {
		return false
	}
	return true
}

func (s *Scheduler) CancelPlan(planID string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	lines, err := s.readCrontab()
	if err != nil {
		return false
	}
	if lines == nil {
		return true
	}
	lines = s.removePlanEntries(lines, planID)
	if err := s.writeCrontab(lines); err != nil {
		return false
	}
	return true
}
