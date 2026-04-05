"""Replace old 4-accordion layout (lines 652-961) with new card layout."""

NEW_BLOCK = """\
                                    <!-- Class Schedule Card -->
                                    <div class="rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40 p-4">
                                        <div class="flex items-center gap-2 mb-3">
                                            <div class="w-6 h-6 rounded-md bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                                                <svg class="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                </svg>
                                            </div>
                                            <div>
                                                <h3 class="text-sm font-semibold text-gray-900 dark:text-white">Class Schedule</h3>
                                                <p class="text-xs text-gray-500 dark:text-gray-400">Daily class scheduling window</p>
                                            </div>
                                        </div>
                                        <div class="grid grid-cols-2 gap-3">
                                            <div>
                                                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Start Time</label>
                                                <div class="custom-time-picker" data-time-picker
                                                     data-name="schedule_start_time" data-id="scheduleStartTime"
                                                     data-value="{{ '%02d:00'|format(active_settings.schedule_start_hour) if active_settings else '07:00' }}"
                                                     data-required="true"
                                                     data-onchange="updateTimePreview(); validateClassTimes();">
                                                </div>
                                            </div>
                                            <div>
                                                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">End Time</label>
                                                <div class="custom-time-picker" data-time-picker
                                                     data-name="schedule_end_time" data-id="scheduleEndTime"
                                                     data-value="{{ '%02d:00'|format(active_settings.schedule_end_hour) if active_settings else '20:00' }}"
                                                     data-required="true"
                                                     data-onchange="updateTimePreview(); validateClassTimes();">
                                                </div>
                                            </div>
                                        </div>
                                        <p id="classTimeError" class="mt-1.5 text-xs text-red-600 dark:text-red-400 hidden flex items-center gap-1">
                                            <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                            End time must be after start time.
                                        </p>
                                        <div class="mt-3 p-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800">
                                            <div class="flex items-center justify-between">
                                                <div class="flex items-center gap-2">
                                                    <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                    </svg>
                                                    <span class="text-xs font-medium text-gray-700 dark:text-gray-300">Daily Schedule Window</span>
                                                </div>
                                                <span id="timeRangePreview" class="text-xs font-semibold text-blue-600 dark:text-blue-400">7:00 AM - 8:00 PM</span>
                                            </div>
                                            <div class="mt-2 flex items-center gap-2">
                                                <div class="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div id="timeRangeBar" class="h-full bg-blue-500 rounded-full transition-all duration-300" style="width: 54%;"></div>
                                                </div>
                                                <span id="totalHoursPreview" class="text-xs font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">13 hours</span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Operation Days Card -->
                                    <div class="rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40 p-4">
                                        <div class="flex items-center gap-2 mb-3">
                                            <div class="w-6 h-6 rounded-md bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
                                                <svg class="w-3.5 h-3.5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                                                </svg>
                                            </div>
                                            <div>
                                                <h3 class="text-sm font-semibold text-gray-900 dark:text-white">Operation Days</h3>
                                                <p class="text-xs text-gray-500 dark:text-gray-400">Days of the week available for scheduling</p>
                                            </div>
                                        </div>
                                        {% set op_days_list = (active_settings.operation_days or 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday').split(',') if active_settings else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'] %}
                                        <div id="operationDaysGroup" class="grid grid-cols-4 sm:grid-cols-7 gap-1.5">
                                            {% set all_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] %}
                                            {% set day_abbr = {'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed', 'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 'Sunday': 'Sun'} %}
                                            {% for day in all_days %}
                                            <label class="day-pill-label flex flex-col items-center gap-1 cursor-pointer rounded-lg border px-2 py-2.5 transition-colors {% if day in op_days_list %}border-green-400 bg-green-50 dark:border-green-600 dark:bg-green-900/30{% else %}border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900{% endif %} hover:border-green-400 dark:hover:border-green-600">
                                                <input type="checkbox" name="operation_days" value="{{ day }}"
                                                       class="sr-only"
                                                       {% if day in op_days_list %}checked{% endif %}
                                                       onchange="updateDayPill(this); updateOperationDaysPreview(); validateOpDays();">
                                                <span class="day-pill-text text-xs font-semibold {% if day in op_days_list %}text-green-700 dark:text-green-300{% else %}text-gray-500 dark:text-gray-400{% endif %}">{{ day_abbr[day] }}</span>
                                            </label>
                                            {% endfor %}
                                        </div>
                                        <p id="opDaysError" class="mt-1.5 text-xs text-red-600 dark:text-red-400 hidden flex items-center gap-1">
                                            <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                            Select at least one operation day.
                                        </p>
                                        <div class="mt-3 p-2.5 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-100 dark:border-green-800">
                                            <div class="flex items-center justify-between">
                                                <div class="flex items-center gap-2">
                                                    <svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                                                    </svg>
                                                    <span class="text-xs font-medium text-gray-700 dark:text-gray-300">Active Days</span>
                                                </div>
                                                <span id="operationDaysPreview" class="text-xs font-semibold text-green-600 dark:text-green-400">{{ op_days_list|length }} day{{ 's' if op_days_list|length != 1 else '' }} selected</span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Exam Schedule Card -->
                                    <div class="rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40 p-4">
                                        <div class="flex items-center gap-2 mb-3">
                                            <div class="w-6 h-6 rounded-md bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center flex-shrink-0">
                                                <svg class="w-3.5 h-3.5 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                                </svg>
                                            </div>
                                            <div>
                                                <h3 class="text-sm font-semibold text-gray-900 dark:text-white">Exam Schedule</h3>
                                                <p class="text-xs text-gray-500 dark:text-gray-400">Exam hours, lunch break, and duration limits</p>
                                            </div>
                                        </div>
                                        <div class="grid grid-cols-2 gap-3">
                                            <div>
                                                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Start Time</label>
                                                <div class="custom-time-picker" data-time-picker
                                                     data-name="exam_start_time" data-id="examStartTime"
                                                     data-value="{{ '%02d:00'|format(active_settings.exam_start_hour) if active_settings else '07:00' }}"
                                                     data-required="true"
                                                     data-onchange="updateExamTimePreview(); validateExamTimes();">
                                                </div>
                                            </div>
                                            <div>
                                                <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">End Time</label>
                                                <div class="custom-time-picker" data-time-picker
                                                     data-name="exam_end_time" data-id="examEndTime"
                                                     data-value="{{ '%02d:00'|format(active_settings.exam_end_hour) if active_settings else '17:00' }}"
                                                     data-required="true"
                                                     data-onchange="updateExamTimePreview(); validateExamTimes();">
                                                </div>
                                            </div>
                                        </div>
                                        <p id="examTimeError" class="mt-1.5 text-xs text-red-600 dark:text-red-400 hidden flex items-center gap-1">
                                            <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                            End time must be after start time.
                                        </p>
                                        <div class="mt-3 p-2.5 bg-orange-50 dark:bg-orange-900/20 rounded-lg border border-orange-100 dark:border-orange-800">
                                            <div class="flex items-center justify-between">
                                                <div class="flex items-center gap-2">
                                                    <svg class="w-4 h-4 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                    </svg>
                                                    <span class="text-xs font-medium text-gray-700 dark:text-gray-300">Exam Schedule Window</span>
                                                </div>
                                                <span id="examTimeRangePreview" class="text-xs font-semibold text-orange-600 dark:text-orange-400">7:00 AM - 5:00 PM</span>
                                            </div>
                                            <div class="mt-2 flex items-center gap-2">
                                                <div class="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div id="examTimeRangeBar" class="h-full bg-orange-500 rounded-full transition-all duration-300" style="width: 42%;"></div>
                                                </div>
                                                <span id="examTotalHoursPreview" class="text-xs font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">10 hours</span>
                                            </div>
                                        </div>
                                        <!-- Advanced Options Toggle -->
                                        <button type="button" id="examAdvancedToggle" onclick="toggleExamAdvanced()"
                                                class="flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors mt-3 mb-2">
                                            <svg id="examAdvancedChevron" class="w-3.5 h-3.5 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                            </svg>
                                            <span id="examAdvancedLabel">Show Advanced Options</span>
                                            <span class="text-gray-400 dark:text-gray-500 font-normal">(lunch break, time slot, duration)</span>
                                        </button>
                                        <!-- Advanced Fields (hidden by default) -->
                                        <div id="examAdvancedFields" class="hidden space-y-4 pt-2 border-t border-dashed border-gray-200 dark:border-gray-700">
                                            <div>
                                                <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Lunch Break</label>
                                                <div class="grid grid-cols-2 gap-3">
                                                    <div>
                                                        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">Start Time</label>
                                                        <div class="custom-time-picker" data-time-picker
                                                             data-name="exam_lunch_start" data-id="examLunchStart"
                                                             data-value="{{ active_settings.exam_lunch_start.strftime('%H:%M') if active_settings and active_settings.exam_lunch_start else '12:00' }}"
                                                             data-required="true"
                                                             data-onchange="updateExamLunchPreview(); validateLunchTimes();">
                                                        </div>
                                                    </div>
                                                    <div>
                                                        <label class="block text-xs text-gray-500 dark:text-gray-400 mb-1">End Time</label>
                                                        <div class="custom-time-picker" data-time-picker
                                                             data-name="exam_lunch_end" data-id="examLunchEnd"
                                                             data-value="{{ active_settings.exam_lunch_end.strftime('%H:%M') if active_settings and active_settings.exam_lunch_end else '13:00' }}"
                                                             data-required="true"
                                                             data-onchange="updateExamLunchPreview(); validateLunchTimes();">
                                                        </div>
                                                    </div>
                                                </div>
                                                <p id="lunchTimeError" class="mt-1.5 text-xs text-red-600 dark:text-red-400 hidden flex items-center gap-1">
                                                    <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                                    Lunch end must be after lunch start.
                                                </p>
                                                <div class="mt-3 p-2.5 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-100 dark:border-yellow-800">
                                                    <div class="flex items-center gap-2">
                                                        <svg class="w-4 h-4 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                                        </svg>
                                                        <span class="text-xs font-medium text-gray-700 dark:text-gray-300">Lunch Break:</span>
                                                        <span id="examLunchPreview" class="text-xs font-semibold text-yellow-700 dark:text-yellow-400">12:00 PM - 1:00 PM</span>
                                                    </div>
                                                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Exams scheduled during this time will show a warning</p>
                                                </div>
                                            </div>
                                            <div class="grid grid-cols-2 gap-3">
                                                <div>
                                                    <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Time Slot Interval</label>
                                                    <select name="exam_slot_duration" id="examSlotDuration" class="form-select" required>
                                                        <option value="30" {% if active_settings and active_settings.exam_slot_duration == 30 %}selected{% elif not active_settings %}selected{% endif %}>30 minutes</option>
                                                        <option value="60" {% if active_settings and active_settings.exam_slot_duration == 60 %}selected{% endif %}>1 hour</option>
                                                        <option value="90" {% if active_settings and active_settings.exam_slot_duration == 90 %}selected{% endif %}>1 hour 30 minutes</option>
                                                        <option value="120" {% if active_settings and active_settings.exam_slot_duration == 120 %}selected{% endif %}>2 hours</option>
                                                    </select>
                                                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Interval between time options</p>
                                                </div>
                                                <div>
                                                    <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Max Exam Duration</label>
                                                    <select name="exam_duration_limit" id="examDurationLimit" class="form-select" required>
                                                        <option value="60" {% if active_settings and active_settings.exam_duration_limit == 60 %}selected{% endif %}>1 hour</option>
                                                        <option value="90" {% if active_settings and active_settings.exam_duration_limit == 90 %}selected{% endif %}>1 hour 30 minutes</option>
                                                        <option value="120" {% if active_settings and active_settings.exam_duration_limit == 120 %}selected{% elif not active_settings %}selected{% endif %}>2 hours</option>
                                                        <option value="150" {% if active_settings and active_settings.exam_duration_limit == 150 %}selected{% endif %}>2 hours 30 minutes</option>
                                                        <option value="180" {% if active_settings and active_settings.exam_duration_limit == 180 %}selected{% endif %}>3 hours</option>
                                                        <option value="240" {% if active_settings and active_settings.exam_duration_limit == 240 %}selected{% endif %}>4 hours</option>
                                                    </select>
                                                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Maximum allowed exam duration</p>
                                                </div>
                                            </div>
                                        </div><!-- /examAdvancedFields -->
                                    </div>

                                    <!-- Faculty Workload Card -->
                                    <div class="rounded-xl border border-gray-100 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40 p-4">
                                        <div class="flex items-center gap-2 mb-3">
                                            <div class="w-6 h-6 rounded-md bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center flex-shrink-0">
                                                <svg class="w-3.5 h-3.5 text-violet-600 dark:text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
                                                </svg>
                                            </div>
                                            <div>
                                                <h3 class="text-sm font-semibold text-gray-900 dark:text-white">Faculty Workload</h3>
                                                <p class="text-xs text-gray-500 dark:text-gray-400">Default teaching unit cap per faculty</p>
                                            </div>
                                        </div>
                                        <div>
                                            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                                                Default Faculty Load Limit
                                                <span class="ml-1 text-xs font-normal text-gray-400">(units)</span>
                                            </label>
                                            <div class="flex items-center gap-3">
                                                <input type="number"
                                                       name="default_faculty_max_units"
                                                       id="defaultFacultyMaxUnits"
                                                       value="{{ active_settings.default_faculty_max_units if active_settings else 24 }}"
                                                       min="1"
                                                       max="99"
                                                       class="form-input w-24 text-center"
                                                       oninput="validateFacultyLoad()"
                                                       required>
                                                <span class="text-sm text-gray-500 dark:text-gray-400">units per faculty</span>
                                            </div>
                                            <p id="facultyLoadError" class="mt-1 text-xs text-red-600 dark:text-red-400 hidden flex items-center gap-1">
                                                <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                                Must be between 1 and 99.
                                            </p>
                                            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Maximum teaching units per faculty. Individual faculty can have custom limits set on the Faculty page.</p>
                                        </div>
                                    </div>

                                </div><!-- /right panel -->

                            </div><!-- /two-column grid -->
"""

with open('app/templates/settings.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines before: {len(lines)}")
print(f"Line 652: {lines[651].rstrip()}")
print(f"Line 961: {lines[960].rstrip()}")

# Replace lines 652-961 (0-indexed 651-960) with the new block
new_lines = lines[:651] + [NEW_BLOCK] + lines[961:]

with open('app/templates/settings.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Total lines after: {len(new_lines)}")
print("Done!")
